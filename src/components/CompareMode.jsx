import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip,
} from 'recharts'

const COLORS = ['#22C55E', '#F97316', '#A78BFA', '#0D9488', '#EF4444']

function exportCSV(results) {
  const headers = ['lat', 'lon', 'composite', 'land', 'gas', 'power', 'npv_p50_m', 'regime']
  const rows = results.map(r => [
    r.lat, r.lon, r.composite_score, r.land_score, r.gas_score,
    r.power_score, r.cost?.npv_p50_m ?? 0, r.regime,
  ])
  const csv = [headers, ...rows].map(row => row.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'collide-comparison.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function radarData(results) {
  const axes = ['Land', 'Gas', 'Power', 'Cost Efficiency']
  return axes.map(axis => {
    const entry = { axis }
    results.forEach((r, i) => {
      const key = `site${i + 1}`
      if (axis === 'Land') entry[key] = r.land_score
      else if (axis === 'Gas') entry[key] = r.gas_score
      else if (axis === 'Power') entry[key] = r.power_score
      else if (axis === 'Cost Efficiency') {
        const npv = r.cost?.npv_p50_m ?? 0
        entry[key] = Math.min(Math.max(npv / 200, 0), 1)
      }
    })
    return entry
  })
}

export default function CompareMode({ results, status, onClose }) {
  if (status === 'loading') {
    return (
      <div className="compare-mode">
        <div className="compare-loading">Evaluating sites…</div>
      </div>
    )
  }
  if (!results || results.length === 0) return null

  return (
    <div className="compare-mode">
      <div className="compare-mode-header">
        <h3 className="compare-mode-title">Site Comparison</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="compare-export-btn" onClick={() => exportCSV(results)}>Export CSV</button>
          <button className="compare-close-btn" onClick={onClose}>✕ Close</button>
        </div>
      </div>

      <div className="compare-table-wrap">
        <table className="compare-table">
          <thead>
            <tr>
              <th>Metric</th>
              {results.map((r, i) => (
                <th key={i} style={{ color: COLORS[i] }}>
                  Site {i + 1}<br />
                  <span style={{ fontSize: 10, fontWeight: 400 }}>
                    ({r.lat.toFixed(3)}, {r.lon.toFixed(3)})
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              { label: 'Composite', key: 'composite_score' },
              { label: 'Land',      key: 'land_score' },
              { label: 'Gas',       key: 'gas_score' },
              { label: 'Power',     key: 'power_score' },
            ].map(({ label, key }) => (
              <tr key={key}>
                <td>{label}</td>
                {results.map((r, i) => {
                  const val = r[key] ?? 0
                  const best = Math.max(...results.map(x => x[key] ?? 0))
                  return (
                    <td key={i} style={{ color: val === best ? '#22C55E' : 'inherit' }}>
                      {r.disqualified
                        ? <span style={{ color: '#EF4444' }}>DQ</span>
                        : Math.round(val * 100)}
                    </td>
                  )
                })}
              </tr>
            ))}
            <tr>
              <td>NPV P50</td>
              {results.map((r, i) => (
                <td key={i}>{r.cost ? `$${r.cost.npv_p50_m.toFixed(0)}M` : '—'}</td>
              ))}
            </tr>
            <tr>
              <td>Regime</td>
              {results.map((r, i) => (
                <td key={i} style={{ fontSize: 10 }}>{r.regime || '—'}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="compare-radar">
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={radarData(results)}>
            <PolarGrid stroke="#2a2520" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: '#9E9589', fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, 1]} tick={false} />
            {results.map((_, i) => (
              <Radar
                key={i}
                name={`Site ${i + 1}`}
                dataKey={`site${i + 1}`}
                stroke={COLORS[i]}
                fill={COLORS[i]}
                fillOpacity={0.15}
              />
            ))}
            <Legend />
            <Tooltip formatter={v => Math.round(v * 100)} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
