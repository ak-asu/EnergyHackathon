import { useState, useEffect, useCallback } from 'react'

export const DEFAULT_CONFIG = {
  maxSites: 5,
  gasPriceMax: null,
  powerCostMax: null,
  acresMin: 0,
  weights: [0.30, 0.35, 0.35],
  marketFilter: [],
  minComposite: 0.0,
}

export function useOptimizeConfig() {
  const [config, setConfig] = useState(DEFAULT_CONFIG)

  const updateConfig = useCallback((partial) => {
    setConfig(prev => ({ ...prev, ...partial }))
  }, [])

  const resetConfig = useCallback(() => setConfig(DEFAULT_CONFIG), [])

  useEffect(() => {
    const handler = e => {
      setConfig(prev => ({ ...prev, ...e.detail }))
      window.dispatchEvent(new CustomEvent('collide:run-optimize'))
    }
    window.addEventListener('collide:set-config', handler)
    return () => window.removeEventListener('collide:set-config', handler)
  }, [])

  return { config, updateConfig, resetConfig }
}
