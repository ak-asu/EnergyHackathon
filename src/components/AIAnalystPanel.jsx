import AgentChat from './AgentChat'
import ContextChipBar from './ContextChipBar'

export default function AIAnalystPanel({ open, onClose, context, chips, onRemoveChip }) {
  return (
    <div className="ai-analyst-panel" style={{ display: open ? undefined : 'none' }}>
      <div className="ai-panel-header">
        <span className="ai-panel-title">⚡ AI Analyst</span>
        <button className="ai-panel-close" onClick={onClose}>✕</button>
      </div>
      {chips && chips.length > 0 && (
        <div className="ai-panel-chips">
          <ContextChipBar chips={chips} onRemove={onRemoveChip} />
        </div>
      )}
      <div className="ai-panel-body">
        <AgentChat context={context} />
      </div>
    </div>
  )
}
