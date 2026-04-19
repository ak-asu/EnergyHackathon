export default function MapStatusIndicator({ mapBusy, label }) {
  if (!mapBusy) return null
  return (
    <div className="map-status-indicator">
      <span className="pulse pulse--green" />
      {label}
    </div>
  )
}
