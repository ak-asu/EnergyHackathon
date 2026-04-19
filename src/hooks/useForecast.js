import { useState, useEffect } from 'react'

const NODES = ['HB_WEST', 'HB_NORTH', 'HB_SOUTH', 'PALOVRDE_ASR-APND']
const DEFAULT_FORECAST = {
  node: 'HB_WEST', horizon: 72,
  p10: Array(72).fill(26), p50: Array(72).fill(34), p90: Array(72).fill(50),
  btm_cost_mwh: 18.64, method: 'fallback',
}

export { NODES }

export function useForecast(initialNode = 'HB_WEST') {
  const [node, setNode] = useState(initialNode)
  const [forecast, setForecast] = useState(DEFAULT_FORECAST)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/forecast?node=${encodeURIComponent(node)}&horizon=72`)
      .then(r => r.json())
      .then(data => { setForecast(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [node])

  return { forecast, node, setNode, loading, availableNodes: NODES }
}
