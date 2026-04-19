import { useState, useCallback } from 'react'

export function useOptimize() {
  const [progress, setProgress] = useState([])
  const [optimal, setOptimal] = useState(null)
  const [status, setStatus]   = useState('idle')

  const optimize = useCallback((bounds, weights = [0.30, 0.35, 0.35]) => {
    setProgress([]); setOptimal(null); setStatus('running')
    fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bounds, weights }),
    }).then(res => {
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = '', event = null
      const read = () => reader.read().then(({ done, value }) => {
        if (done) { setStatus('done'); return }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim()
          if (line.startsWith('data: ') && event) {
            const d = JSON.parse(line.slice(6).trim())
            if (event === 'progress') setProgress(p => [...p, d])
            if (event === 'optimal')  setOptimal(d)
            event = null
          }
        }
        read()
      })
      read()
    }).catch(() => setStatus('error'))
  }, [])

  const reset = useCallback(() => {
    setProgress([]); setOptimal(null); setStatus('idle')
  }, [])

  return { progress, optimal, status, optimize, reset }
}
