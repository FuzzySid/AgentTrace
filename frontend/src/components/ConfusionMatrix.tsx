import type { ConfusionMatrix as Matrix } from '../lib/api'
export default function ConfusionMatrix({ data }: { data: Matrix }) {
  const max = Math.max(...data.matrix.flat(), 1)
  return <section className="matrix-card"><div className="matrix-title"><h3>Attribution accuracy vs ground truth</h3><b>{(data.accuracy * 100).toFixed(1)}%</b></div><table className="matrix"><thead><tr><th>GT\\PR</th>{data.labels.map(l => <th key={l}>{l.slice(0, 4)}</th>)}</tr></thead><tbody>{data.matrix.map((row, i) => <tr key={data.labels[i]}><th>{data.labels[i].slice(0, 4)}</th>{row.map((n,j)=><td key={j} className={i===j ? 'correct' : n ? 'incorrect' : ''} style={n ? { opacity: .35 + .65 * n / max } : undefined}>{n || '·'}</td>)}</tr>)}</tbody></table></section>
}
