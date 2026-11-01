export type SortMetric = 'progressive_passes_attempted_per90' | 'progressive_passes_completed_per90' | 'progressive_pass_completion_pct' | 'progressive_carries_per90' | 'overall_pass_completion_pct'
export type SortDirection = 'asc' | 'desc'
export type ScoutingSearchFilters = {
  profile: 'ball_progressing_midfielder'
  min_minutes: number
  min_central_share_pct: number
  sort_by: SortMetric
  sort_direction: SortDirection
  limit: number
}

export function buildScoutingUrl(filters: ScoutingSearchFilters): string
export function nextSortDirection(activeKey: SortMetric, activeDirection: SortDirection, targetKey: SortMetric): SortDirection
export function formatRate(value: number | null | undefined): string
export function formatPercentage(value: number | null | undefined): string
