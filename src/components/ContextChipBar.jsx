function chipLabel(chip) {
  if (chip.type === 'region') return 'Selected region'
  if (chip.type === 'site') return chip.payload?.name || 'Site'
  if (chip.type === 'coord') {
    const { lat, lon } = chip.payload
    return `${lat?.toFixed(3)}, ${lon?.toFixed(3)}`
  }
  return chip.type
}

function chipClass(type) {
  if (type === 'region') return 'citation-chip citation-chip--green'
  if (type === 'site')   return 'citation-chip citation-chip--orange'
  return 'citation-chip citation-chip--blue'
}

export default function ContextChipBar({ chips, onRemove }) {
  if (!chips || chips.length === 0) return null
  return (
    <div className="context-chip-bar">
      {chips.map((chip, i) => (
        <span key={i} className={chipClass(chip.type)}>
          {chipLabel(chip)}
          <button
            className="chip-dismiss"
            onClick={() => onRemove(i)}
            aria-label={`Remove ${chipLabel(chip)}`}
          >×</button>
        </span>
      ))}
    </div>
  )
}
