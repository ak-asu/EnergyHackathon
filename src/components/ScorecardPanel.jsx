import { useState } from 'react'
import SummaryTab from './SummaryTab'
import EconomicsTab from './EconomicsTab'
import RiskTab from './RiskTab'

const TABS = ['Summary', 'Economics', 'Risk']

export default function ScorecardPanel({ scorecard, narrative, status, error, onClose }) {
  const [tab, setTab] = useState('Summary')
  if (!scorecard && status === 'idle') return null

  return (
    <div className="scorecard-panel">
      <div className="scorecard-panel-header">
        <div className="scorecard-panel-loc">
          {scorecard
            ? `(${scorecard.lat.toFixed(4)}, ${scorecard.lon.toFixed(4)})`
            : 'Loading…'}
        </div>
        <button className="scorecard-panel-close" onClick={onClose}>✕</button>
      </div>

      {scorecard?.hard_disqualified ? (
        <div className="scorecard-disqualified">
          <div className="scorecard-dq-icon">⛔</div>
          <div className="scorecard-dq-reason">{scorecard.disqualify_reason}</div>
        </div>
      ) : (
        <>
          <div className="scorecard-tabs">
            {TABS.map(t => (
              <button
                key={t}
                className={`scorecard-tab${tab === t ? ' scorecard-tab--active' : ''}`}
                onClick={() => setTab(t)}
              >{t}</button>
            ))}
          </div>
          {tab === 'Summary'   && <SummaryTab scorecard={scorecard} narrative={narrative} status={status} error={error} />}
          {tab === 'Economics' && <EconomicsTab scorecard={scorecard} />}
          {tab === 'Risk'      && <RiskTab scorecard={scorecard} />}
        </>
      )}
    </div>
  )
}
