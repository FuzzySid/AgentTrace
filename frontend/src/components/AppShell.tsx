import { useQuery } from '@tanstack/react-query'
import { fetchRuns } from '../lib/api'

export type Screen = 'traces' | 'cost' | 'regressions' | 'telemetry'
const items: { id: Screen; label: string; icon: string }[] = [
  { id: 'traces', label: 'Traces', icon: '⌘' }, { id: 'cost', label: 'Cost', icon: '▣' }, { id: 'regressions', label: 'Regressions', icon: '⇄' }, { id: 'telemetry', label: 'Telemetry', icon: '⌁' },
]
export default function AppShell({ screen, onScreen, runId, onRunChange, children }: { screen: Screen; onScreen: (screen: Screen) => void; runId: string; onRunChange: (id: string) => void; children: React.ReactNode }) {
  const runs = useQuery({ queryKey: ['runs'], queryFn: fetchRuns })
  const selected = runs.data?.find(r => r.run_id === runId)
  return <div className="min-h-screen bg-page text-ink">
    <aside className="sidebar"><div><div className="brand"><svg viewBox="0 0 28 28" aria-hidden="true"><g fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="7" cy="6" r="2.3" fill="currentColor"/><circle cx="7" cy="22" r="2.3" fill="currentColor"/><circle cx="21" cy="14" r="2.3"/><path d="M7 8.3v11.4M9.3 14H18.7"/></g></svg><span>AgentTrace</span></div><nav className="side-nav">{items.map(item => <button key={item.id} onClick={() => onScreen(item.id)} className={screen === item.id ? 'nav-item active' : 'nav-item'}><span className="nav-icon">{item.icon}</span>{item.label}</button>)}</nav></div><div className="tier-box"><span>tier:</span><b>attrs</b></div></aside>
    <div className="app-main"><header className="topbar"><div className="run-context"><span className="brand-mark">⌘</span><span className="brand-name">AgentTrace</span><select aria-label="Select run" value={runId} onChange={e => onRunChange(e.target.value)}>{runs.data?.map(run => <option key={run.run_id} value={run.run_id}>{run.label}</option>)}</select><span className="muted">· {selected?.task_count ?? '—'} tasks</span><span className="tag">{selected?.capture_tier ?? 'attrs'}</span><span className="pass-text">● {selected?.passed ?? '—'} passed</span><span className="fail-text">● {selected?.failed ?? '—'} failed</span></div><div className="top-actions"><span className="control">◷ &nbsp;Last 2h</span><span className="control">prod-agent-cluster-04</span><span className="control">⌘K &nbsp;palette</span><span className="avatar">♙</span></div></header><main className="content">{children}</main></div>
  </div>
}
