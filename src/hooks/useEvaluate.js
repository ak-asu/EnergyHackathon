import { useState, useCallback, useRef } from 'react'

const INITIAL = { status: 'idle', scorecard: null, narrative: '', error: null }

async function readErrorMessage(res) {
  const fallback = `Evaluation failed (${res.status})`
  const contentType = res.headers.get('content-type') || ''

  try {
    if (contentType.includes('application/json')) {
      const body = await res.json()
      return body.message || body.error || fallback
    }

    const text = await res.text()
    return text || fallback
  } catch {
    return fallback
  }
}

export function useEvaluate() {
  const [state, setState] = useState(INITIAL)
  const abortRef = useRef(null)

  const evaluate = useCallback(async (lat, lon, weights = [0.30, 0.35, 0.35]) => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ status: 'loading', scorecard: null, narrative: '', error: null })

    try {
      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lon, weights }),
        signal: controller.signal,
      })

      if (!res.ok) {
        throw new Error(await readErrorMessage(res))
      }

      if (!res.body) {
        throw new Error('API did not return a stream')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let event = null
      let receivedScorecard = false

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const rawLine of lines) {
          const line = rawLine.trimEnd()
          if (line.startsWith('event: ')) {
            event = line.slice(7).trim()
            continue
          }

          if (line.startsWith('data: ') && event) {
            const data = line.slice(6).trim()
            if (event === 'scorecard') {
              receivedScorecard = true
              setState(s => ({ ...s, status: 'streaming', scorecard: JSON.parse(data) }))
            } else if (event === 'narrative') {
              try {
                const chunk = JSON.parse(data)
                setState(s => ({ ...s, narrative: s.narrative + chunk }))
              } catch (_) {}
            }
            event = null
          }
        }
      }

      if (controller.signal.aborted) return
      if (!receivedScorecard) {
        throw new Error('No scorecard data returned by API')
      }

      setState(s => ({ ...s, status: 'done' }))
    } catch (err) {
      if (err?.name === 'AbortError') return
      setState({ status: 'error', scorecard: null, narrative: '', error: err.message })
    }
  }, [])

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setState(INITIAL)
  }, [])

  return { ...state, evaluate, reset }
}
