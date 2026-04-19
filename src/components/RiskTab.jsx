import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const STRESS_SCENARIOS = [
  { id: 'uri',    label: 'Uri Equivalent', gasAdj: +2.0, lmpMult: 0.3 },
  { id: 'gas40',  label: 'Gas +40%',       gasAdj: +0.7, lmpMult: 1.0 },
  { id: 'wind3',  label: '3-Day Wind Curtailment', gasAdj: 0, lmpMult: 0.4 },
  { id: 'lmp2x',  label: 'LMP ×2',         gasAdj: 0, lmpMult: 2.0 },
]

export default function RiskTab({ scorecard: sc }) {
  const [activeScenario, setActiveScenario] = useState(null)

  if (!sc) return null

  const baseSpread = sc.spread_p50_mwh
  const shap = sc.land_shap || {}
  const shapData = Object.entries(shap)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 6)
    .map(([k, v]) => ({ factor: k, value: +v.toFixed(3) }))

  const scenarioResult = activeScenario
    ? (() => {
        const s = STRESS_SCENARIOS.find(x => x.id === activeScenario)
        const adjSpread = (baseSpread - s.gasAdj * 8.5) * s.lmpMult
        const npvImpact = ((adjSpread - baseSpread) * 100 * 8760 * 20) / 1e6
        return { adjSpread: adjSpread.toFixed(1), npvImpact: npvImpact.toFixed(0) }
      })()
    : null

  return (
    <div className="risk-tab">
      <h4>Stress Tests</h4>
      <div className="stress-buttons">
        {STRESS_SCENARIOS.map(s => (
          <button
            key={s.id}
            className={`stress-btn${activeScenario === s.id ? ' stress-btn--active' : ''}`}
            onClick={() => setActiveScenario(activeScenario === s.id ? null : s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {scenarioResult && (
        <div className="stress-result">
          <span>Adj. spread: <b>${scenarioResult.adjSpread}/MWh</b></span>
          <span>NPV impact: <b>${scenarioResult.npvImpact}M</b></span>
        </div>
      )}

      <h4 style={{ marginTop: 16 }}>Land Score Attribution (SHAP)</h4>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={shapData} layout="vertical">
          <XAxis type="number" />
          <YAxis dataKey="factor" type="category" width={70} />
          <Tooltip />
          <Bar dataKey="value">
            {shapData.map((d, i) => (
              <Cell key={i} fill={d.value >= 0 ? '#22C55E' : '#EF4444'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
