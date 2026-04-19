import BriefingCard from './BriefingCard'
import AgentChat from './AgentChat'
import { useRegime } from '../hooks/useRegime'

export default function AIAnalystPanel({ open, onClose, context, chips, onRemoveChip, ask, reset, tokens, citations, agentStatus }) {
  const regime = useRegime()
  if (!open) return null
  return (
    <div className="ai-analyst-panel">
      <div className="ai-panel-header">
        <span className="ai-panel-title">⚡ AI Analyst</span>
        <button className="ai-panel-close" onClick={onClose}>✕</button>
      </div>
      <div className="ai-panel-body">
        <BriefingCard regime={regime} />
        <div className="ai-panel-divider" />
        <AgentChat
          context={context} chips={chips} onRemoveChip={onRemoveChip}
          ask={ask} reset={reset} tokens={tokens} citations={citations} status={agentStatus}
        />
      </div>
    </div>
  )
}
