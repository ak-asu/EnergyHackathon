import { useState, useEffect } from 'react'
import { DEFAULT_CONFIG } from '../hooks/useOptimizeConfig'

function adjustWeights(weights, changedIdx, newVal) {
  const clamped = Math.max(0.05, Math.min(0.90, newVal))
  const others = weights.filter((_, i) => i !== changedIdx)
  const othersSum = others.reduce((a, b) => a + b, 0)
  const remaining = +(1 - clamped).toFixed(2)
  const result = weights.map((w, i) => {
    if (i === changedIdx) return clamped
    if (othersSum === 0) return +(remaining / 2).toFixed(2)
    return +(w / othersSum * remaining).toFixed(2)
  })
  const sum = result.reduce((a, b) => a + b, 0)
  const diff = +(1 - sum).toFixed(2)
  if (diff !== 0) {
    const adjustIdx = result.findIndex((_, i) => i !== changedIdx)
    result[adjustIdx] = +(result[adjustIdx] + diff).toFixed(2)
  }
  return result
}

const MARKETS = ['ERCOT', 'CAISO', 'SPP']
const WEIGHT_LABELS = ['Land', 'Gas', 'Power']

export default function OptimizeConfigDialog({ open, config, onApply, onReset, onClose }) {
  const [local, setLocal] = useState(config)

  useEffect(() => { setLocal(config) }, [config])

  if (!open) return null

  const handleWeightChange = (idx, val) => {
    setLocal(prev => ({ ...prev, weights: adjustWeights(prev.weights, idx, parseFloat(val)) }))
  }

  const toggleMarket = (market) => {
    setLocal(prev => {
      const next = prev.marketFilter.includes(market)
        ? prev.marketFilter.filter(m => m !== market)
        : [...prev.marketFilter, market]
      return { ...prev, marketFilter: next }
    })
  }

  return (
    <div className="config-dialog-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="config-dialog">
        <div className="config-dialog-header">
          <span className="config-dialog-title">Optimization Config</span>
          <button className="config-dialog-close" onClick={onClose}>✕</button>
        </div>
        <div className="config-dialog-body">
          <label className="config-label">Max sites to find
            <input type="number" min={1} max={10} className="config-input"
              value={local.maxSites}
              onChange={e => setLocal(prev => ({ ...prev, maxSites: Math.max(1, Math.min(10, parseInt(e.target.value) || 1)) }))} />
          </label>
          <label className="config-label">Min composite score ({Math.round(local.minComposite * 100)}%)
            <input type="range" min={0.50} max={0.95} step={0.01} className="config-slider"
              value={local.minComposite}
              onChange={e => setLocal(prev => ({ ...prev, minComposite: parseFloat(e.target.value) }))} />
          </label>
          <label className="config-label">Gas price max ($/MMBtu)
            <input type="number" min={0} step={0.1} placeholder="No limit" className="config-input"
              value={local.gasPriceMax ?? ''}
              onChange={e => setLocal(prev => ({ ...prev, gasPriceMax: e.target.value === '' ? null : parseFloat(e.target.value) }))} />
          </label>
          <label className="config-label">Power cost max ($/MWh)
            <input type="number" min={0} step={1} placeholder="No limit" className="config-input"
              value={local.powerCostMax ?? ''}
              onChange={e => setLocal(prev => ({ ...prev, powerCostMax: e.target.value === '' ? null : parseFloat(e.target.value) }))} />
          </label>
          <label className="config-label">Min parcel size (acres)
            <input type="number" min={0} step={100} className="config-input"
              value={local.acresMin}
              onChange={e => setLocal(prev => ({ ...prev, acresMin: parseInt(e.target.value) || 0 }))} />
          </label>
          <div className="config-label">Market filter
            <div className="config-market-row">
              {MARKETS.map(m => (
                <label key={m} className="config-market-check">
                  <input type="checkbox" checked={local.marketFilter.length === 0 || local.marketFilter.includes(m)}
                    onChange={() => toggleMarket(m)} />
                  {m}
                </label>
              ))}
            </div>
          </div>
          <div className="config-label">Score weights (must sum to 1)
            {WEIGHT_LABELS.map((label, i) => (
              <label key={label} className="config-weight-row">
                <span className="config-weight-label">{label} ({(local.weights[i] * 100).toFixed(0)}%)</span>
                <input type="range" min={0.05} max={0.90} step={0.01} className="config-slider"
                  value={local.weights[i]}
                  onChange={e => handleWeightChange(i, e.target.value)} />
              </label>
            ))}
          </div>
        </div>
        <div className="config-dialog-footer">
          <button className="config-btn config-btn--ghost" onClick={() => { onReset(); setLocal(DEFAULT_CONFIG) }}>Reset</button>
          <button className="config-btn config-btn--primary" onClick={() => { onApply(local); onClose() }}>Apply</button>
        </div>
      </div>
    </div>
  )
}
