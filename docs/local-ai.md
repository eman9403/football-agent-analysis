# Local AI setup and evaluation

The app's normal shortlist search and evidence dossier work without an LLM. Local AI adds natural-language filter proposals and selects which verified metrics to emphasize. It uses LangChain's `ChatOllama` integration to reach an Ollama service on this Mac; the model never writes SQL or creates metric values. There is no OpenAI API key or per-call API bill.

## Current machine state

The Ollama app and model are optional, and no model has been downloaded as part of Sprint 4 implementation. Until you choose to install one, `/api/ai/status` reports that local AI is unavailable, question interpretation stays disabled, manual filters continue to work, and the reporting lens creates a deterministic evidence-only dossier.

## Enable a first local model

The starter model configured by the app is `qwen3.5:4b`. Ollama currently lists this tag at about 4.0 GB to download; it will use additional working memory while generating a response. That is a disk commitment you can reverse later. The 4B tag is a candidate to measure on the M1 Pro, not a claim that it is the best fit.

1. Install and open [Ollama for macOS](https://ollama.com/download).
2. In Terminal, pull the configured model:

   ```bash
   ollama pull qwen3.5:4b
   ```

3. Restart the workbench if it is already open, or use **CHECK AGAIN** beside the local model status. The AI question box becomes available when the local Ollama service and configured model are both present.
4. Enter a question and inspect its proposed lens, thresholds, and sort metric. Select **APPLY PROPOSAL** to run it. The model never applies a filter on its own.

To use another Ollama model already downloaded on the machine, set `OLLAMA_MODEL` when starting the app, for example `OLLAMA_MODEL=qwen3.5:2b ./infra/dev.sh`. Only loopback Ollama addresses are accepted. The app defaults to `http://127.0.0.1:11434`; it does not send prompts or player evidence to a hosted model service.

## Check disk and memory use

```bash
ollama ls
ollama ps
```

`ollama ls` lists downloaded models. `ollama ps` lists models currently loaded in memory; Ollama's local `/api/ps` response also includes loaded model size and the amount assigned to accelerator memory. On Apple silicon, shared memory means those fields are model-placement details, not a complete measure of all RAM currently in use.

The fixed benchmark samples Ollama process resident memory while it tests question interpretation and records model sizes, median/p95 latency, and exact filter accuracy:

```bash
backend/.venv/bin/python -m backend.run_local_ai_evals
```

It writes the run under `evals/results/`, which is ignored by Git. The evaluation questions contain no player-level data. Compare model choices using the same case file and configuration before deciding which should be the default.

## Remove the model

When you want the disk space back, stop the running model and remove its downloaded files:

```bash
ollama stop qwen3.5:4b
ollama rm qwen3.5:4b
```

Removing the weights frees their disk space. Closing the model or running `ollama stop` releases its working memory; memory used by PostgreSQL, the API, browser, and other apps is separate.

## What is covered by the evaluation

`evals/sprint-4-local-ai.json` contains supported requests for all four profile lenses, ambiguous questions, unsupported fields (including expected assists/xA and current-season claims), and the report evidence contract. The report model can choose only metric keys supplied by the API. The API checks the keys and whether a proposed highlight or watchpoint meets its percentile threshold, then writes the number, unit, peer cohort, metric definition, season, and StatsBomb source revision into the displayed claim. Invalid selections fall back to deterministic evidence selection.

The real M1 Pro latency, memory, filter accuracy, and report-selection quality remain unmeasured until Ollama and a model are installed and the benchmark is run.
