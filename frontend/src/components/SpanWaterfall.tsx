import type { Span, TraceDetail } from '../lib/api'
const colors: Record<string, string> = { plan: 'bar-alt', retrieve: 'bar-pass', synthesize: 'bar-purple', tool: 'bar-fail', critique_loop: 'bar-warn', agent: 'bar-blue' }
export default function SpanWaterfall({ trace }: { trace: TraceDetail }) {
  const max = Math.max(...trace.spans.map(s => s.start_ms + s.duration_ms), 1)
  const ticks = [0, .25, .5, .75, 1]
  return <section className="panel waterfall"><div className="panel-head"><div><h2>Execution waterfall timeline</h2><span className="muted">Span hierarchy and elapsed time</span></div><div className="legend"><i className="dot bar-alt"/>Plan/model <i className="dot bar-pass"/>Retrieval <i className="dot bar-fail"/>Fault origin <i className="dot bar-warn"/>Symptom</div></div><div className="water-head"><div>Span hierarchy</div><div className="axis">{ticks.map(t => <span key={t} style={{ left: `${t * 100}%` }}>{Math.round(max * t)}ms</span>)}</div></div>
    {trace.spans.map((span: Span) => {
      const primary = span.span_id === trace.primary_failure_span_id
      const symptom = trace.secondary_symptom_span_ids.includes(span.span_id)
      return <div className={`span-row ${primary ? 'primary-failure' : ''} ${symptom ? 'secondary-failure' : ''}`} key={span.span_id}>
        <div className="span-label" style={{ paddingLeft: `${12 + span.depth * 20}px` }}><span className="tree-guide">{span.depth ? '├─' : '⌄'}</span><span>{span.name}</span>{primary && <em>PRIMARY FAILURE</em>}{symptom && <em className="symptom">SYMPTOM</em>}</div>
        <div className="track"><i className={`span-bar ${colors[span.operation_name ?? ''] ?? 'bar-blue'}`} style={{ left: `${span.start_ms / max * 100}%`, width: `${Math.max(span.duration_ms / max * 100, 1)}%` }}><span>{span.duration_ms.toLocaleString()}ms</span></i></div>
      </div>
    })}</section>
  }
