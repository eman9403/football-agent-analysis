export function buildScoutingUrl(filters) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  return `/api/scouting/players?${params.toString()}`
}

export function nextSortDirection(activeKey, activeDirection, targetKey) {
  return activeKey === targetKey && activeDirection === 'desc' ? 'asc' : 'desc'
}

export function formatRate(value) {
  return value === null || value === undefined ? '—' : Number(value).toFixed(2)
}

export function formatPercentage(value) {
  return value === null || value === undefined ? '—' : `${Number(value).toFixed(1)}%`
}

export function formatMetric(value, unit) {
  return unit === 'percent' ? formatPercentage(value) : formatRate(value)
}
