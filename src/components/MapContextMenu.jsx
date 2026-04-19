import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

export default function MapContextMenu({
  open, x, y, target, committedBounds,
  onClose, onEvaluate, onAddCompare, onSendToAgent, onSetRegionCenter,
}) {
  const menuRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const handleKey = e => { if (e.key === 'Escape') onClose() }
    const handleClick = e => {
      if (menuRef.current && !menuRef.current.contains(e.target)) onClose()
    }
    document.addEventListener('keydown', handleKey)
    document.addEventListener('mousedown', handleClick)
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.removeEventListener('mousedown', handleClick)
    }
  }, [open, onClose])

  if (!open || !target) return null

  const isSite = target.type === 'site'

  return createPortal(
    <div
      ref={menuRef}
      className="map-context-menu"
      style={{ position: 'fixed', top: y, left: x, zIndex: 9999 }}
    >
      {isSite ? (
        <>
          <button className="map-ctx-item" onClick={() => { onEvaluate(target.site.lat, target.site.lng); onClose() }}>
            Evaluate site
          </button>
          <button className="map-ctx-item" onClick={() => { onAddCompare(target.site.lat, target.site.lng); onClose() }}>
            Add to compare
          </button>
          <button className="map-ctx-item" onClick={() => { onSendToAgent({ type: 'site', payload: target.site }); onClose() }}>
            Send to agent
          </button>
          {committedBounds && (
            <button className="map-ctx-item" onClick={() => { onSetRegionCenter(target.site.lat, target.site.lng); onClose() }}>
              Set as region center
            </button>
          )}
        </>
      ) : (
        <>
          <button className="map-ctx-item" onClick={() => { onEvaluate(target.lat, target.lon); onClose() }}>
            Evaluate this location
          </button>
          <button className="map-ctx-item" onClick={() => { onAddCompare(target.lat, target.lon); onClose() }}>
            Add compare pin here
          </button>
          <button className="map-ctx-item" onClick={() => { onSendToAgent({ type: 'coord', payload: { lat: target.lat, lon: target.lon } }); onClose() }}>
            Send location to agent
          </button>
        </>
      )}
    </div>,
    document.body
  )
}
