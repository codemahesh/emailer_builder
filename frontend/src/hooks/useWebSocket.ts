import { useEffect, useRef, useCallback } from 'react'
import { type ImageProcessingProgress } from '../lib/api'

export function useWebSocket(
  campaignId: string | undefined,
  onMessage: (msg: ImageProcessingProgress) => void,
) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  // Keep a stable ref to the latest onMessage callback so the connect closure
  // never goes stale without triggering a reconnect.
  const onMessageRef = useRef(onMessage)
  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  const connect = useCallback(() => {
    if (!campaignId) return

    const wsUrl = `${
      import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    }/ws/${campaignId}`

    try {
      ws.current = new WebSocket(wsUrl)
    } catch {
      // WebSocket constructor can throw synchronously on bad URLs
      return
    }

    ws.current.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as ImageProcessingProgress
        onMessageRef.current(msg)
      } catch {
        // Ignore non-JSON frames (e.g. "pong")
      }
    }

    ws.current.onclose = () => {
      // Reconnect after 3 s unless we intentionally closed
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    ws.current.onerror = () => {
      // Let onclose handle reconnect
      ws.current?.close()
    }

    // Ping every 30 s to keep the connection alive through proxies / load balancers
    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send('ping')
      }
    }, 30000)

    // Return cleanup for this particular connection instance
    return () => {
      clearInterval(pingInterval)
    }
  }, [campaignId]) // onMessage intentionally excluded — handled via ref

  useEffect(() => {
    const cleanup = connect()
    return () => {
      cleanup?.()
      clearTimeout(reconnectTimer.current)
      // Close without triggering reconnect: remove onclose first
      if (ws.current) {
        ws.current.onclose = null
        ws.current.close()
        ws.current = null
      }
    }
  }, [connect])
}
