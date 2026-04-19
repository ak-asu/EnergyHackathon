import { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { useForecast, NODES } from '../hooks/useForecast'

function buildChartData(forecast, gasAdj, lmpMult) {
  const { p10, p50, p90, btm_cost_mwh } = forecast
  return Array.from({ length: p50.length }, (_, i) => ({
    h: i,
    p50: +((p50[i] * lmpMult - btm_cost_mwh - gasAdj * 8.5)).toFixed(2),
    p10: +((p10[i] * lmpMult - btm_cost_mwh - gasAdj * 8.5)).toFixed(2),
    p90: +((p90[i] * lmpMult - btm_cost_mwh - gasAdj * 8.5)).toFixed(2),
  }))
}

export default function EconomicsTab({ scorecard: sc }) {
  const [gasAdj, setGasAdj] = useState(0)
  const [lmpMult, setLmpMult] = useState(1.0)

  const defaultNode = sc?.ercot_node || 'HB_WEST'
  const { forecast, node, setNode, loading } = useForecast(defaultNode)

  useEffect(() => {
    if (sc?.ercot_node) setNode(sc.ercot_node)
  }, [sc?.ercot_node, setNode])

  if (!sc) return null

  const data = buildChartData(forecast, gasAdj, lmpMult)
  const cost = sc.cost

  return (
    <div className="economics-tab">
      <div className="econ-header">
        <h4 className="econ-title">72-Hour BTM Spread Forecast</h4>
        <select
          className="node-selector"
          value={node}
          onChange={e => setNode(e.target.value)}
        >
          {NODES.map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        {loading && <span className="econ-loading">…</span>}
      </div>

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
