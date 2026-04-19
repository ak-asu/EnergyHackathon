import { useState, useEffect } from 'react'

const FALLBACK = { HB_WEST: 42.0, HB_NORTH: 40.0, HB_SOUTH: 43.0 }

export function useLmpStream() {
  const [lmp, setLmp] = useState(FALLBACK)

  useEffect(() => {
    let ws
    const connect = () => {
      ws = new WebSocket(`ws://${location.host}/api/lmp/stream`)
      ws.onmessage = e => setLmp(JSON.parse(e.data))
      ws.onclose   = () => setTimeout(connect, 5000)
    }
    connect()
    return () => ws?.close()
  }, [])

  return lmp
}
