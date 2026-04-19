import { useLmpStream } from '../hooks/useLmpStream'
import { useRegime } from '../hooks/useRegime'
import { useMarket } from '../hooks/useApi'

const REGIME_LABELS = {
  normal:           { color: '#22C55E', text: 'Normal — balanced grid' },
  stress_scarcity:  { color: '#EF4444', text: 'Stress / Scarcity — high LMP' },
  wind_curtailment: { color: '#F59E0B', text: 'Wind Curtailment — grid cheap' },
}

export default function BottomStrip() {
  const lmp    = useLmpStream()
  const regime = useRegime()
  const { market } = useMarket()
  const rl = REGIME_LABELS[regime.label] || REGIME_LABELS.normal

  return (
    <div className="bottom-strip">
      <div className="bs-regime">
        <span className="bs-regime-dot" style={{ background: rl.color }} />
        <span className="bs-regime-text">{rl.text}</span>
      </div>

      <div className="bs-lmp-ticker">
        {Object.entries(lmp).map(([node, price]) => (
          <span key={node} className="bs-lmp-item">
            {node}: <b>${price.toFixed(1)}</b>/MWh
          </span>
        ))}
      </div>

      <div className="bs-fuel-mix">
        <span>Waha: <b>${(market?.wahaHub?.price ?? 1.84).toFixed(2)}</b>/MMBtu</span>
        <span>Palo Verde: <b>${(market?.paloverdeL?.price ?? 38.5).toFixed(1)}</b>/MWh</span>
      </div>
    </div>
  )
}
