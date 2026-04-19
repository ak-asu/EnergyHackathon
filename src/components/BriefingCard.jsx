import { useEffect } from 'react'
import { useAgent } from '../hooks/useAgent'

export default function BriefingCard({ regime }) {
  const { tokens, citations, status, ask, reset } = useAgent()

  useEffect(() => {
    ask(
      'Give me a current market briefing: (1) current regime state and what it means for BTM economics, ' +
      '(2) the strongest siting opportunity right now and why, (3) the top risk to watch.',
      { regime }
    )
    return reset
  }, [])  // fire once on mount

  const sections = tokens.split(/\n\n+/).filter(Boolean)

  return (
    <div className="briefing-card">
      <div className="briefing-card-header">
        <span className="briefing-card-title">Market Briefing</span>
        <button
          className="briefing-refresh-btn"
          onClick={() => {
            reset()
            ask(
              'Give me a current market briefing: (1) current regime and BTM economics, ' +
              '(2) strongest siting opportunity, (3) top risk.',
              { regime }
            )
          }}
          disabled={status === 'loading' || status === 'streaming'}
        >
          {status === 'loading' || status === 'streaming' ? '…' : '↺'}
        </button>
      </div>

      {status === 'error' && (
        <div className="briefing-error">Analysis unavailable — check ANTHROPIC_API_KEY</div>
      )}

      {status === 'loading' && (
        <div className="briefing-thinking">Analyzing market conditions…</div>
      )}

      {sections.length > 0 && (
        <div className="briefing-sections">
          {sections.map((text, i) => (
            <div key={i} className="briefing-section">{text}</div>
          ))}
        </div>
      )}

      {citations.length > 0 && (
        <div className="briefing-citations">
          {citations.slice(0, 4).map((c, i) => (
            <span key={i} className="citation-chip citation-chip--blue">{c}</span>
          ))}
        </div>
      )}
    </div>
  )
}
