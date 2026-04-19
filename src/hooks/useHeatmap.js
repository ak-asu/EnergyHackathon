import { useState, useCallback } from 'react'

export function useHeatmap() {
  const [features, setFeatures] = useState([])
  const [activeLayer, setActiveLayer] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadLayer = useCallback((layer) => {
    if (activeLayer === layer) {
      setFeatures([])
      setActiveLayer(null)
      return
    }
    setLoading(true)
    fetch(`/api/heatmap?layer=${layer}`)
      .then(r => r.json())
      .then(geojson => {
        setFeatures(geojson.features || [])
        setActiveLayer(layer)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [activeLayer])

  const clearLayer = useCallback(() => {
    setFeatures([])
    setActiveLayer(null)
  }, [])

  return { features, activeLayer, loading, loadLayer, clearLayer }
}
