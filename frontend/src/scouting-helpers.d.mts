export type ProfileKey = 'ball_progressing_midfielder' | 'chance_creating_attacker' | 'forward_finisher' | 'ball_winning_midfielder'
export type SortMetric = 'progressive_passes_attempted_per90' | 'progressive_passes_completed_per90' | 'progressive_pass_completion_pct' | 'progressive_carries_per90' | 'overall_pass_completion_pct' | 'shot_assists_per90' | 'goal_assists_per90' | 'completed_box_passes_per90' | 'shots_per90' | 'expected_goals_per90' | 'goals_per90' | 'expected_goals_per_shot' | 'pressures_per90' | 'ball_recoveries_per90' | 'interceptions_per90' | 'interception_positive_outcome_pct' | 'tackle_duels_per90' | 'tackle_positive_outcome_pct'
export type SortDirection = 'asc' | 'desc'
export type ScoutingSearchFilters = {
  profile: ProfileKey
  min_minutes: number
  min_role_share_pct: number
  sort_by: SortMetric
  sort_direction: SortDirection
  limit: number
}

export function buildScoutingUrl(filters: ScoutingSearchFilters): string
export function nextSortDirection(activeKey: SortMetric, activeDirection: SortDirection, targetKey: SortMetric): SortDirection
export function formatRate(value: number | null | undefined): string
export function formatPercentage(value: number | null | undefined): string
export function formatMetric(value: number | null | undefined, unit: string): string
