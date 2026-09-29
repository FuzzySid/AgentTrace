import { useState } from 'react'
import AppShell, { type Screen } from './components/AppShell'
import TraceExplorer from './components/TraceExplorer'
import CostDashboard from './components/CostDashboard'
import RegressionCompare from './components/RegressionCompare'
import TelemetryTax from './components/TelemetryTax'

export default function App() {
  const [screen, setScreen] = useState<Screen>('traces')
  const [runId, setRunId] = useState('run_001')
  return <AppShell screen={screen} onScreen={setScreen} runId={runId} onRunChange={setRunId}>
    {screen === 'traces' && <TraceExplorer runId={runId} />}
    {screen === 'cost' && <CostDashboard runId={runId} />}
    {screen === 'regressions' && <RegressionCompare />}
    {screen === 'telemetry' && <TelemetryTax runId={runId} />}
  </AppShell>
}
