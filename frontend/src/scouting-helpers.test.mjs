import assert from 'node:assert/strict'
import test from 'node:test'

let helpers = {}
try {
  helpers = await import('./scouting-helpers.mjs')
} catch {
  // The helper module is introduced after this test demonstrates the missing behavior.
}

test('search URL includes only the typed filter contract', () => {
  assert.equal(typeof helpers.buildScoutingUrl, 'function', 'scouting URL helper is not implemented')
  const url = new URL(helpers.buildScoutingUrl({
    profile: 'ball_progressing_midfielder',
    min_minutes: 900,
    min_central_share_pct: 75,
    sort_by: 'progressive_carries_per90',
    sort_direction: 'asc',
    limit: 12,
  }), 'http://local.test')

  assert.equal(url.pathname, '/api/scouting/players')
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    profile: 'ball_progressing_midfielder',
    min_minutes: '900',
    min_central_share_pct: '75',
    sort_by: 'progressive_carries_per90',
    sort_direction: 'asc',
    limit: '12',
  })
})

test('sort direction toggles only for the active metric', () => {
  assert.equal(typeof helpers.nextSortDirection, 'function', 'sort direction helper is not implemented')
  assert.equal(helpers.nextSortDirection('progressive_carries_per90', 'desc', 'progressive_carries_per90'), 'asc')
  assert.equal(helpers.nextSortDirection('progressive_carries_per90', 'asc', 'progressive_carries_per90'), 'desc')
  assert.equal(helpers.nextSortDirection('progressive_passes_completed_per90', 'asc', 'overall_pass_completion_pct'), 'desc')
})

test('metric formatting handles unavailable percentages and per-90 values', () => {
  assert.equal(typeof helpers.formatRate, 'function', 'metric formatting helpers are not implemented')
  assert.equal(typeof helpers.formatPercentage, 'function', 'metric percentage formatter is not implemented')
  assert.equal(helpers.formatRate(null), '—')
  assert.equal(helpers.formatRate(3.456), '3.46')
  assert.equal(helpers.formatPercentage(null), '—')
  assert.equal(helpers.formatPercentage(72.56), '72.6%')
})
