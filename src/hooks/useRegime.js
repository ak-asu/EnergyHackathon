import { useState, useEffect } from 'react'

export function useRegime() {
  const [regime, setRegime] = useState({ label: 'normal', proba: [1, 0, 0] })

  useEffect(() => {
    const load = () => fetch('/api/regime')
      .then(r => r.json())
      .then(setRegime)
      .catch(() => {})
    load()
    const id = setInterval(load, 5 * 60 * 1000)
    return () => clearInterval(id)
  }, [])

  return regime
}
