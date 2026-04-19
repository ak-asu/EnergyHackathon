import { useState, useCallback, useRef } from 'react'

const INITIAL = { status: 'idle', tokens: '', citations: [], error: null }

export function useAgent() {
  const [state, setState] = useState(INITIAL)
  const abortRef = useRef(null)

  const ask = useCallback((query, context = {}) => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setState({ status: 'loading', tokens: '', citations: [], error: null })

    fetch('/api/agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, context }),
      signal: controller.signal,
    }).then(res => {
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const read = () => reader.read().then(({ done, value }) => {
        if (done) { setState(s => ({ ...s, status: 'done' })); return }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        let event = null
        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim()
          if (line.startsWith('data: ') && event) {
            const data = line.slice(6).trim()
            if (event === 'token') {
              setState(s => ({ ...s, status: 'streaming', tokens: s.tokens + data }))
            } else if (event === 'citation') {
              setState(s => ({ ...s, citations: [...s.citations, data] }))
            } else if (event === 'error') {
              setState(s => ({ ...s, status: 'error', error: data }))
            }
            event = null
          }
        }
        read()
      }).catch(() => {})
      read()
    }).catch(err => {
      if (err.name !== 'AbortError') {
        setState(s => ({ ...s, status: 'error', error: err.message }))
      }
    })
  }, [])

  const reset = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
    setState(INITIAL)
  }, [])

  return { ...state, ask, reset }
}
