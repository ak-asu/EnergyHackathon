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
      if (!res.ok) {
        setState(s => ({ ...s, status: 'error', error: `API ${res.status} — is the backend running?` }))
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let event = null

      const read = () => reader.read().then(({ done, value }) => {
        if (done) { setState(s => ({ ...s, status: 'done' })); return }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim()
          if (line.startsWith('data: ') && event) {
            const raw = line.slice(6).trim()
            if (event === 'token') {
              try {
                const token = JSON.parse(raw)
                setState(s => ({ ...s, status: 'streaming', tokens: s.tokens + token }))
              } catch (_) {}
            } else if (event === 'citation') {
              setState(s => ({ ...s, citations: [...s.citations, raw] }))
            } else if (event === 'error') {
              setState(s => ({ ...s, status: 'error', error: raw }))
            } else if (event === 'config_update') {
              try {
                const payload = JSON.parse(raw)
                window.dispatchEvent(new CustomEvent('collide:set-config', { detail: payload }))
              } catch (_) {}
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
