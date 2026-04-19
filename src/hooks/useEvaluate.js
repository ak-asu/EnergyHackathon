import { useState, useCallback, useRef } from 'react'

const INITIAL = { status: 'idle', scorecard: null, narrative: '', error: null }

export function useEvaluate() {
  const [state, setState] = useState(INITIAL)
  const esRef = useRef(null)

  const evaluate = useCallback((lat, lon, weights = [0.30, 0.35, 0.35]) => {
    if (esRef.current) esRef.current.close()
    setState({ status: 'loading', scorecard: null, narrative: '', error: null })

    fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lon, weights }),
    }).then(res => {
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const read = () => reader.read().then(({ done, value }) => {
        if (done) {
          setState(s => ({ ...s, status: 'done' }))
          return
        }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        let event = null
        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim()
          if (line.startsWith('data: ') && event) {
            const data = line.slice(6).trim()
            if (event === 'scorecard') {
              setState(s => ({ ...s, status: 'streaming', scorecard: JSON.parse(data) }))
            } else if (event === 'narrative') {
              setState(s => ({ ...s, narrative: s.narrative + data }))
            }
            event = null
          }
        }
        read()
      })
      read()
    }).catch(err => {
      setState({ status: 'error', scorecard: null, narrative: '', error: err.message })
    })
  }, [])

  const reset = useCallback(() => {
    if (esRef.current) esRef.current.close()
    setState(INITIAL)
  }, [])

  return { ...state, evaluate, reset }
}
