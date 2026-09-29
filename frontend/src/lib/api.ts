export type Run = { run_id: string; label: string; task_count: number; passed: number; failed: number; capture_tier: string }
export type TraceRow = { task_id: string; trace_id: string; status: 'failed' | 'passed'; failure_class: string | null; duration_ms: number; cost_eur: number; span_count: number }
export type Span = { span_id: string; parent_span_id: string | null; name: string; depth: number; start_ms: number; duration_ms: number; status: string; operation_name: string | null; tokens_in: number | null; tokens_out: number | null; attributes: Record<string, unknown> }
export type TraceDetail = { trace_id: string; task_id: string; capture_tier: string; primary_failure_span_id: string | null; secondary_symptom_span_ids: string[]; spans: Span[] }
export type ConfusionMatrix = { labels: string[]; matrix: number[][]; accuracy: number }
export type CostSummary = { median_cost_eur: number; median_cost_successful_eur: number; cost_per_successful_session_eur: number; p50_latency_ms: number; p95_latency_ms: number; cost_by_span_type: Record<string, number>; distribution: { bucket_eur: number; count: number }[]; top_sessions: { task_id: string; cost_eur: number; duration_ms: number; span_count: number; status: string; input_tokens: number; output_tokens: number }[]; sessions: { trace_id: string; task_id: string; status: string; input_tokens: number; output_tokens: number; cost_eur: number; evaluation_input_tokens: number; evaluation_output_tokens: number; evaluation_cost_eur: number; duration_ms: number; span_count: number }[]; production_cost_eur: number; evaluation_cost_eur: number; evaluation_input_tokens: number; evaluation_output_tokens: number; total_input_tokens: number; total_output_tokens: number; session_count: number; successful_session_count: number }
export type Regression = { baseline: { run_id: string; prompt_version: string; model_tier: string; task_count: number; passed: number; failed: number }; candidate: { run_id: string; prompt_version: string; model_tier: string; task_count: number; passed: number; failed: number }; paired_task_count: number; failure_rate: { baseline: number; candidate: number }; cost_per_success_eur: { baseline: number; candidate: number }; p95_latency_ms: { baseline: number; candidate: number }; newly_failing: { task_id: string; failure_class: string | null }[]; newly_fixed: { task_id: string }[] }
export type Telemetry = { tiers: { tier: string; span_count: number; total_bytes: number; bytes_per_session: number; ratio_vs_full: number }[]; capabilities: { question: string; full: 'success' | 'degrades' | 'fails'; attrs: 'success' | 'degrades' | 'fails'; sampled: 'success' | 'degrades' | 'fails' }[]; recommendation: { default_tier: string; tradeoff: string } }

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json() as Promise<T>
}
export const fetchRuns = () => get<Run[]>('/api/runs')
export const fetchTraces = (runId: string) => get<TraceRow[]>(`/api/traces?run_id=${encodeURIComponent(runId)}`)
export const fetchTrace = (traceId: string) => get<TraceDetail>(`/api/traces/${encodeURIComponent(traceId)}`)
export const fetchConfusionMatrix = (runId: string) => get<ConfusionMatrix>(`/api/traces/confusion-matrix?run_id=${encodeURIComponent(runId)}`)
export const fetchCost = (runId: string) => get<CostSummary>(`/api/cost/summary?run_id=${encodeURIComponent(runId)}`)
export const fetchRegressions = (comparison: 'prompt' | 'tier', baseline?: string, candidate?: string) => get<Regression>(`/api/regressions?comparison=${encodeURIComponent(comparison)}${baseline ? `&baseline=${encodeURIComponent(baseline)}` : ''}${candidate ? `&candidate=${encodeURIComponent(candidate)}` : ''}`)
export const fetchTelemetry = (runId: string) => get<Telemetry>(`/api/telemetry/tax?run_id=${encodeURIComponent(runId)}`)
