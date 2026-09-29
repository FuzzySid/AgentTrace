import { useQuery } from '@tanstack/react-query'
import { fetchCost } from '../lib/api'

const money = (value: number) => `€${value.toFixed(6)}`
const duration = (value: number) => value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${value.toFixed(0)}ms`

export default function CostDashboard({ runId }: { runId: string }) {
  const q = useQuery({ queryKey: ['cost', runId], queryFn: () => fetchCost(runId) })
  if (q.isLoading) return <div className="state">Loading cost summary…</div>
  if (q.isError || !q.data) return <div className="state fail-text">Could not load cost summary.</div>
  const d = q.data
  const max = Math.max(...d.distribution.map(item => item.count), 1)
  const colors = ['bg-alt', 'bg-accent', 'bg-fail', 'bg-pass']
  const breakdownTotal = Object.values(d.cost_by_span_type).reduce((sum, value) => sum + value, 0)
  return <div className="screen-stack">
    <div className="page-heading"><div><h1>◉ Run Unit Economics & Tail Latency</h1><p className="muted">{runId} · {d.session_count} sessions · production work excludes evaluation calls</p></div><div className="heading-total">Production spend: <b>{money(d.production_cost_eur)}</b><br/><span className="muted">Evaluation spend: {money(d.evaluation_cost_eur)}</span></div></div>
    <div className="metric-grid four">
      {[["MEDIAN COST / SESSION", money(d.median_cost_eur), `${d.session_count} production sessions`, ''], ["COST / SUCCESSFUL SESSION", money(d.cost_per_successful_session_eur), `${d.successful_session_count} successful sessions`, 'target'], ['P50 WALL-CLOCK LATENCY', duration(d.p50_latency_ms), 'root span duration', ''], ['P95 WALL-CLOCK LATENCY', duration(d.p95_latency_ms), 'root span duration', 'warn']].map(([label, value, foot, kind]) => <section className={`panel metric ${kind === 'target' ? 'target' : ''}`} key={label}><div className="metric-label">{label}</div><strong className={kind === 'warn' ? 'warn-text' : ''}>{value}</strong><span className="muted">{foot}</span></section>)}
    </div>
    <section className="panel token-summary"><div><h2>Token totals</h2><p className="muted">Calculated from provider-reported usage on exported spans.</p></div><div><b>{d.total_input_tokens.toLocaleString()}</b><span> production input</span></div><div><b>{d.total_output_tokens.toLocaleString()}</b><span> production output</span></div><div><b>{d.evaluation_input_tokens.toLocaleString()} / {d.evaluation_output_tokens.toLocaleString()}</b><span> evaluation input / output</span></div></section>
    <div className="two-columns"><section className="panel chart-panel"><h2>▮ Session cost distribution</h2><p className="muted">{d.distribution.reduce((sum, item) => sum + item.count, 0)} production sessions</p><div className="histogram">{d.distribution.map((bucket, index) => <div className="hist-col" key={bucket.bucket_eur}><div className={`hist-bar ${index < Math.ceil(d.distribution.length / 2) ? 'pass-bg' : 'fail-bg'}`} style={{ height: `${Math.max(8, bucket.count / max * 82)}%` }}/><small>{money(bucket.bucket_eur)}</small><small>{bucket.count}</small></div>)}</div></section>
      <section className="panel breakdown"><h2>◉ Cost by node type</h2><p className="muted">Production token charges only · {money(breakdownTotal)} categorized</p><div className="stacked">{Object.entries(d.cost_by_span_type).map(([key, value], index) => <i key={key} className={colors[index % colors.length]} style={{ width: `${breakdownTotal ? value / breakdownTotal * 100 : 0}%` }} title={`${key}: ${money(value)}`}/>)}</div><div className="breakdown-list">{Object.entries(d.cost_by_span_type).map(([key, value], index) => <div key={key}><span><i className={`dot ${colors[index % colors.length]}`}/>{key.replace('_', ' ')}</span><b>{money(value)}</b><small>{breakdownTotal ? (value / breakdownTotal * 100).toFixed(1) : '0.0'}%</small></div>)}</div></section></div>
    <section className="panel data-table"><div className="panel-head"><h2>▤ Most expensive sessions <span className="muted">(production cost)</span></h2><span className="muted">Top {d.top_sessions.length} traces</span></div><table><thead><tr><th>Task ID</th><th>Status</th><th className="right">Cost</th><th className="right">Duration</th><th className="right">Tokens in / out</th><th>Spans</th></tr></thead><tbody>{d.top_sessions.map(session => <tr key={session.task_id}><td className="mono">task_{session.task_id}</td><td><span className={`badge ${session.status === 'failed' ? 'fail' : 'pass'}`}>● {session.status}</span></td><td className="right mono">{money(session.cost_eur)}</td><td className="right mono">{duration(session.duration_ms)}</td><td className="right mono">{session.input_tokens.toLocaleString()} / {session.output_tokens.toLocaleString()}</td><td className="right mono">{session.span_count}</td></tr>)}</tbody></table><footer className="table-foot">Evaluation-tagged spans are priced separately and excluded from production session cost.<span>Currency: EUR (€) · ISO 4217</span></footer></section>
  </div>
}
