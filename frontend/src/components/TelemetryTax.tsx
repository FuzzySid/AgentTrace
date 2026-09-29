import { useQuery } from '@tanstack/react-query'
import { fetchTelemetry } from '../lib/api'

const pretty = (bytes: number) => bytes >= 1_000_000 ? `${(bytes / 1_000_000).toFixed(2)} MB` : bytes >= 1000 ? `${(bytes / 1000).toFixed(1)} KB` : `${Math.round(bytes)} B`
const badge = (result: 'success' | 'degrades' | 'fails') => result === 'success' ? ['pass-text', '✓ success'] : result === 'degrades' ? ['warn-text', '△ degrades'] : ['fail-text', '× fails']

export default function TelemetryTax({ runId }: { runId: string }) {
  const q = useQuery({ queryKey: ['telemetry', runId], queryFn: () => fetchTelemetry(runId) })
  if (q.isLoading) return <div className="state">Loading telemetry analysis…</div>
  if (q.isError || !q.data) return <div className="state fail-text">Could not load telemetry analysis.</div>
  const d = q.data
  const fullBytes = d.tiers.find(tier => tier.tier === 'full')?.total_bytes ?? 0
  const attrs = d.tiers.find(tier => tier.tier === 'attrs')
  return <div className="screen-stack"><div className="page-heading"><div><label>TELEMETRY PROTOCOL / OVERHEAD TRADEOFFS</label><h1>Telemetry Overhead & Capture Tiers</h1><p className="muted">Measurements and diagnostic attempts from the captured fixture runs.</p></div><div className="drain"><div><small>ATTRIBUTES CAPTURE</small><b className="pass-text">{pretty(attrs?.total_bytes ?? 0)} / run</b></div><div><small>RATIO TO FULL</small><b>{attrs?.ratio_vs_full.toFixed(3) ?? '0.000'}×</b></div></div></div>
    <div className="tier-grid">{d.tiers.map(tier => <section className={`panel tier-card ${tier.tier === d.recommendation.default_tier ? 'current' : ''}`} key={tier.tier}><div className="panel-head"><h2>{tier.tier === 'attrs' ? 'Attributes only' : tier.tier === 'sampled' ? 'Sampled 10%' : 'Full'}</h2><span className="badge">{tier.ratio_vs_full.toFixed(3)}×</span></div>{tier.tier === d.recommendation.default_tier && <span className="accent-text">● Recommended routine capture</span>}<p className="muted tier-description">{tier.tier === 'full' ? 'All span attributes and opt-in prompt/completion content events.' : tier.tier === 'attrs' ? 'GenAI and AgentTrace attributes with content events removed.' : 'Attributes capture sampled at the exporter; error roots are retained.'}</p><div className="tier-stats"><span>Span count</span><b>{tier.span_count.toLocaleString()}</b><span>Ingestion volume</span><b>{pretty(tier.total_bytes)}</b><span>Bytes per session</span><b>{pretty(tier.bytes_per_session)}</b></div><div className="progress"><i style={{ width: `${fullBytes ? Math.max(2, tier.ratio_vs_full * 100) : 0}%` }} className={tier.tier === 'full' ? 'pass-bg' : tier.tier === 'attrs' ? 'bg-accent' : 'warn-bg'}/></div></section>)}</div>
    <section className="capabilities"><div className="panel-head"><div><h2>Diagnostic capability attempts</h2><p className="muted">Each cell records an attempt against that tier’s captured spans.</p></div><div className="legend"><i className="dot pass-bg"/>Success <i className="dot warn-bg"/>Degrades <i className="dot fail-bg"/>Fails</div></div><table><thead><tr><th>Question attempted</th><th>Full</th><th className="current-col">Attrs</th><th>Sampled</th></tr></thead><tbody>{d.capabilities.map(row => <tr key={row.question}><td>{row.question}</td>{(['full', 'attrs', 'sampled'] as const).map(tier => { const [className, label] = badge(row[tier]); return <td className={tier === 'attrs' ? 'current-col' : ''} key={tier}><span className={className}>{label}</span></td> })}</tr>)}</tbody></table></section>
    <section className="panel recommendation"><div><h2>✿ Default Recommendation for Production Agents</h2><p>{d.recommendation.tradeoff}</p></div><span className="badge">Default: {d.recommendation.default_tier}</span></section>
  </div>
}
