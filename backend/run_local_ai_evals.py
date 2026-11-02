"""Run fixed interpretation cases and sample local Ollama process memory."""

import argparse
import json
import re
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from backend.local_ai import (
    InvalidModelOutput,
    LocalModelUnavailable,
    OllamaStatus,
    interpret_question,
)
from backend.scouting import ScoutingFilters


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals" / "sprint-4-local-ai.json"
RESULTS = ROOT / "evals" / "results"


def _ollama_rss_mib() -> float | None:
    try:
        completed = subprocess.run(
            ["ps", "-A", "-o", "rss=,comm="],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    rss_kib = 0
    found = False
    for line in completed.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2 or "ollama" not in parts[1].casefold():
            continue
        try:
            rss_kib += int(parts[0])
            found = True
        except ValueError:
            continue
    return round(rss_kib / 1024, 1) if found else 0.0


class MemorySampler:
    def __init__(self, interval_seconds: float = 0.2):
        self.interval_seconds = interval_seconds
        self.samples: list[float] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self):
        while not self._stop.is_set():
            value = _ollama_rss_mib()
            if value is not None:
                self.samples.append(value)
            self._stop.wait(self.interval_seconds)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join(timeout=3)

    @property
    def peak_mib(self) -> float | None:
        return max(self.samples) if self.samples else None


def _loaded_models(base_url: str) -> list[dict] | None:
    try:
        with urlopen(f"{base_url.rstrip('/')}/api/ps", timeout=1) as response:
            payload = json.loads(response.read())
    except Exception:
        return None
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return None
    return [
        {
            "name": model.get("name"),
            "loaded_size_bytes": model.get("size"),
            "vram_size_bytes": model.get("size_vram"),
        }
        for model in models
        if isinstance(model, dict)
    ]


def _actual_filters_match(actual, expected: dict) -> tuple[bool, list[str]]:
    if actual is None:
        return False, ["expected filters, got no proposal"]
    errors = []
    for key, expected_value in expected.items():
        actual_value = getattr(actual, key)
        if actual_value != expected_value:
            errors.append(f"{key}: expected {expected_value!r}, got {actual_value!r}")
    return not errors, errors


def _evaluate_cases(cases: list[dict], sampler: MemorySampler) -> list[dict]:
    results = []
    for case in cases:
        start = time.perf_counter()
        row = {
            "id": case["id"],
            "expected_decision": case["expected_decision"],
            "status": "error",
            "matches": False,
            "latency_ms": None,
            "errors": [],
        }
        try:
            result = interpret_question(case["question"], ScoutingFilters())
            row["status"] = result.status
            row["matches"] = result.status == case["expected_decision"]
            if result.status == "ready":
                expected = case.get("expected_filters", {})
                filter_match, filter_errors = _actual_filters_match(result.proposed_filters, expected)
                row["matches"] = row["matches"] and filter_match
                row["errors"] = filter_errors
                row["actual_filters"] = result.proposed_filters.model_dump()
            elif result.proposed_filters is not None:
                row["matches"] = False
                row["errors"] = ["clarification/unsupported result included runnable filters"]
        except (LocalModelUnavailable, InvalidModelOutput, ValueError) as error:
            row["errors"] = [str(error)]
        row["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
        if sampler.samples:
            row["ollama_rss_peak_mib_so_far"] = sampler.peak_mib
        results.append(row)
        print(f"{case['id']}: {'PASS' if row['matches'] else 'FAIL'} ({row['latency_ms']} ms)")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON result path (default: ignored evals/results/).")
    args = parser.parse_args()

    status = OllamaStatus.inspect()
    if not status.available:
        raise SystemExit(f"Cannot run model evaluations: {status.detail}")

    suite = json.loads(EVALS.read_text())
    baseline_memory = _ollama_rss_mib()
    with MemorySampler() as sampler:
        cases = _evaluate_cases(suite["filter_cases"], sampler)
    passes = sum(case["matches"] for case in cases)
    latencies = sorted(case["latency_ms"] for case in cases if case["latency_ms"] is not None)
    p95_index = min(len(latencies) - 1, int(len(latencies) * 0.95)) if latencies else 0
    report = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "model": status.model,
        "ollama_base_url": status.base_url,
        "case_count": len(cases),
        "passed": passes,
        "decision_and_filter_accuracy": round(passes / len(cases), 4) if cases else 0,
        "latency_ms": {
            "median": round(latencies[len(latencies) // 2], 1) if latencies else None,
            "p95": round(latencies[p95_index], 1) if latencies else None,
        },
        "memory": {
            "ollama_process_rss_baseline_mib": baseline_memory,
            "ollama_process_rss_peak_mib": sampler.peak_mib,
            "sample_count": len(sampler.samples),
            "loaded_model_sizes": _loaded_models(status.base_url),
            "measurement_note": "RSS samples sum macOS processes whose command contains 'ollama'; model size is also read from Ollama /api/ps.",
        },
        "cases": cases,
        "report_claim_contract": suite["report_contract"],
    }
    output_path = args.output
    if output_path is None:
        RESULTS.mkdir(parents=True, exist_ok=True)
        safe_model = re.sub(r"[^a-zA-Z0-9-]+", "-", status.model).strip("-").lower()
        output_path = RESULTS / f"sprint-4-{safe_model}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Filter accuracy: {passes}/{len(cases)} ({report['decision_and_filter_accuracy']:.0%})")
    print(f"Local run written to ignored result path: {output_path}")
    if passes != len(cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
