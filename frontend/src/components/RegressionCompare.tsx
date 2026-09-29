import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchRegressions } from '../lib/api'

export default function RegressionCompare() {
  const [comparison, setComparison] = useState<'prompt' | 'tier'>('prompt')
  const q = useQuery({ queryKey: ['regressions', comparison], queryFn: () => fetchRegressions(comparison) })
  if (q.isLoading) return <div className="state">Loading paired run comparison…</div>
  if (q.isError || !q.data) return <div className="state fail-text">Could not load run comparison.</div>
  const d = q.data
  const tierOutcome = d.cost_per_success_eur.baseline > d.cost_per_success_eur.candidate
    ? `The cheap tier cost €${d.cost_per_success_eur.baseline.toFixed(6)} per successful session, above mid at €${d.cost_per_success_eur.candidate.toFixed(6)}.`
    : `In this paired run, cheap did not cost more per successful session than mid (€${d.cost_per_success_eur.baseline.toFixed(6)} vs €${d.cost_per_success_eur.candidate.toFixed(6)}).`
  const metrics = [
    ['FAILURE RATE', `${(d.failure_rate.baseline * 100).toFixed(1)}%`, `${(d.failure_rate.candidate * 100).toFixed(1)}%`, 'fail'],
    ['COST / SUCCESSFUL SESSION', `€${d.cost_per_success_eur.baseline.toFixed(6)}`, `€${d.cost_per_success_eur.candidate.toFixed(6)}`, 'pass'],
    ['P95 WALL-CLOCK LATENCY', `${(d.p95_latency_ms.baseline / 1000).toFixed(2)}s`, `${(d.p95_latency_ms.candidate / 1000).toFixed(2)}s`, 'warn'],
  ]
  const sides = [{ run: d.baseline, label: 'BASELINE' }, { run: d.candidate, label: 'CANDIDATE' }]
  return <div className="screen-stack">
    <section className="panel compare-head"><div className="panel-head"><h2>⇄ Paired run comparison</h2><select aria-label="Comparison" value={comparison} onChange={event => setComparison(event.target.value as 'prompt' | 'tier')}><option value="prompt">Verbose vs terse prompt</option><option value="tier">Cheap vs mid tier</option></select></div><div className="run-compare">{sides.map(({ run, label }) => <div key={run.run_id}><label>{label}</label><h3>◷ {run.run_id}</h3><span className="badge">{run.prompt_version}</span> <span className="badge">{run.model_tier}</span><p>{run.task_count} paired tasks <span className="pass-text">{run.passed} passed</span> · <span className="fail-text">{run.failed} failed</span></p></div>)}</div><p className="muted">Metrics use the {d.paired_task_count} task IDs present in both runs.</p></section>
    {comparison === 'tier' && <section className={`panel ${d.cost_per_success_eur.baseline > d.cost_per_success_eur.candidate ? 'fail-text' : 'muted'}`}><h2>Measured tier result</h2><p>{tierOutcome}</p></section>}
    <div className="metric-grid three">{metrics.map(([name, base, candidate, tone]) => <section className="panel diff-metric" key={name}><label>{name}</label><div><span><small>BASELINE</small><b>{base}</b></span><span className="arrow">→</span><span className={tone === 'fail' ? 'fail-text' : tone === 'pass' ? 'pass-text' : 'warn-text'}><small>CANDIDATE</small><b>{candidate}</b></span></div></section>)}</div>
    <section className="panel data-table"><div className="panel-head"><div><h2><span className="fail-text">●</span> Newly failing tasks</h2><p className="muted">Passed in baseline and failed in candidate.</p></div><span className="badge fail">{d.newly_failing.length} regressions</span></div><table><thead><tr><th>Task ID</th><th>Baseline</th><th>Candidate</th><th>Failure class</th></tr></thead><tbody>{d.newly_failing.map(task => <tr key={task.task_id}><td className="mono">task_{task.task_id}</td><td><span className="badge pass">passed</span></td><td><span className="badge fail">failed</span></td><td><span className="badge fail">{task.failure_class ?? 'unclassified'}</span></td></tr>)}{!d.newly_failing.length && <tr><td colSpan={4} className="muted">No newly failing paired tasks.</td></tr>}</tbody></table></section>
    <section className="panel data-table"><div className="panel-head"><div><h2><span className="pass-text">●</span> Newly fixed tasks</h2><p className="muted">Failed in baseline and passed in candidate.</p></div><span className="badge pass">{d.newly_fixed.length} fixed</span></div><table><thead><tr><th>Task ID</th><th>Baseline</th><th>Candidate</th></tr></thead><tbody>{d.newly_fixed.map(task => <tr key={task.task_id}><td className="mono">task_{task.task_id}</td><td><span className="badge fail">failed</span></td><td><span className="badge pass">passed</span></td></tr>)}{!d.newly_fixed.length && <tr><td colSpan={3} className="muted">No newly fixed paired tasks.</td></tr>}</tbody></table></section>
  </div>
}
