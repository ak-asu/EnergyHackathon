import { useState, useCallback } from 'react'

const MAX_SITE_CHIPS = 3

export function useMapContext() {
  const [chips, setChips] = useState([])

  const addChip = useCallback((chip) => {
    setChips(prev => {
      const regions = prev.filter(c => c.type === 'region')
      const others = prev.filter(c => c.type !== 'region')
      if (chip.type === 'region') {
        return [chip, ...others]
      }
      const newOthers = [chip, ...others].slice(0, MAX_SITE_CHIPS)
      return [...regions, ...newOthers]
    })
  }, [])

  const removeChip = useCallback((index) => {
    setChips(prev => prev.filter((_, i) => i !== index))
  }, [])

  const clearChips = useCallback(() => setChips([]), [])

  return { chips, addChip, removeChip, clearChips }
}
