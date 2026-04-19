import { useState, useCallback } from 'react'

export function useCompare() {
  const [pins, setPins] = useState([])          // [{lat, lon}]
  const [results, setResults] = useState([])    // ranked scorecards from /api/compare
  const [status, setStatus] = useState('idle')  // idle | loading | done | error

  const addPin = useCallback((lat, lon) => {
    setPins(prev => {
      if (prev.length >= 5) return prev
      const exists = prev.some(p => Math.abs(p.lat - lat) < 0.001 && Math.abs(p.lon - lon) < 0.001)
      return exists ? prev : [...prev, { lat, lon }]
    })
  }, [])

  const removePin = useCallback((index) => {
    setPins(prev => prev.filter((_, i) => i !== index))
    setResults([])
    setStatus('idle')
  }, [])

  const clearPins = useCallback(() => {
    setPins([])
    setResults([])
    setStatus('idle')
  }, [])

  const runCompare = useCallback(() => {
    if (pins.length < 2) return
    setStatus('loading')
    const coordStr = pins.map(p => `${p.lat},${p.lon}`).join(';')
    fetch(`/api/compare?coords=${encodeURIComponent(coordStr)}`)
      .then(r => r.json())
      .then(data => { setResults(data); setStatus('done') })
      .catch(() => setStatus('error'))
  }, [pins])

  return { pins, results, status, addPin, removePin, clearPins, runCompare }
}
