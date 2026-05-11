import { useEffect, useRef, useCallback } from 'react'
import type { WSMessage } from '../types'

export function useWebSocket(onMessage: (msg: WSMessage) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const ws = new WebSocket(`${protocol}://${host}/ws`)

    ws.onopen = () => console.log('[WS] connected')
    ws.onclose = () => {
      console.log('[WS] disconnected, reconnecting in 3s...')
      setTimeout(connect, 3000)
    }
    ws.onerror = (e) => console.error('[WS] error', e)
    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        onMessageRef.current(msg)
      } catch {}
    }
    wsRef.current = ws
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])
}
