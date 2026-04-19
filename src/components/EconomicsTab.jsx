import { useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

function mockForecast(spread_p50) {
  return Array.from({ length: 72 }, (_, i) => ({
    h: i,
    p50: +(spread_p50 + Math.sin(i / 6) * 4).toFixed(2),
    p10: +(spread_p50 - 8 + Math.sin(i / 6) * 4).toFixed(2),
    p90: +(spread_p50 + 8 + Math.sin(i / 6) * 4).toFixed(2),
  }))
}

export default function EconomicsTab({ scorecard: sc }) {
  const [gasAdj, setGasAdj] = useState(0)
  const [lmpMult, setLmpMult] = useState(1.0)

  if (!sc) return null

  const adjSpread = sc.spread_p50_mwh - gasAdj * 8.5
  const data = mockForecast(adjSpread * lmpMult)
  const cost = sc.cost

  return (
    <div className="economics-tab">
      <h4 className="econ-title">72-Hour BTM Spread Forecast</h4>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data}>
          <XAxis dataKey="h" label={{ value: 'Hours', position: 'insideBottom', offset: -5 }} />
          <YAxis unit="$/MWh" />
          <Tooltip formatter={v => `$${v}/MWh`} />
          <ReferenceLine y={0} stroke="#EF4444" strokeDasharray="4 4" />
          <Area dataKey="p90" stroke="none" fill="#22C55E" fillOpacity={0.15} />
          <Area dataKey="p50" stroke="#22C55E" fill="none" strokeWidth={2} />
          <Area dataKey="p10" stroke="none" fill="#EF4444" fillOpacity={0.10} />
        </AreaChart>
      </ResponsiveContainer>

      <div className="sliders">
        <div className="slider-row">
          <label>Gas ±${gasAdj.toFixed(1)}/MMBtu</label>
          <input type="range" min="-2" max="2" step="0.1" value={gasAdj}
            onChange={e => setGasAdj(+e.target.value)} />
        </div>
        <div className="slider-row">
          <label>LMP {lmpMult.toFixed(1)}×</label>
          <input type="range" min="0.5" max="3" step="0.1" value={lmpMult}
            onChange={e => setLmpMult(+e.target.value)} />
        </div>
      </div>

      {cost && (
        <div className="cost-breakdown">
          <h4>20-Year Cost Breakdown</h4>
          <table className="cost-table">
            <tbody>
              <tr><td>BTM Capex</td><td>${cost.btm_capex_m.toFixed(0)}M</td></tr>
              <tr><td>Land</td><td>${cost.land_acquisition_m.toFixed(1)}M</td></tr>
              <tr><td>Gas Pipeline</td><td>${cost.pipeline_connection_m.toFixed(1)}M</td></tr>
              <tr><td>Water</td><td>${cost.water_connection_m.toFixed(1)}M</td></tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
