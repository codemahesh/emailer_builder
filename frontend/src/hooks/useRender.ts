import { useState, useCallback, useRef } from 'react'
import { renderCampaign, type RenderResult } from '../lib/api'

export function useRender(campaignId: string | undefined) {
  const [html, setHtml] = useState<string | undefined>()
  const [renderResult, setRenderResult] = useState<RenderResult | undefined>()
  const [isRendering, setIsRendering] = useState(false)
  const [error, setError] = useState<string | undefined>()
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>()

  const render = useCallback(async () => {
    if (!campaignId) return
    setIsRendering(true)
    setError(undefined)
    try {
      const result = await renderCampaign(campaignId)
      setHtml(result.html)
      setRenderResult(result)
    } catch {
      setError('Render failed')
    } finally {
      setIsRendering(false)
    }
  }, [campaignId])

  // Debounced render: call triggerRender() after any layout-affecting change
  const triggerRender = useCallback(() => {
    clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(render, 800)
  }, [render])

  return { html, renderResult, isRendering, error, render, triggerRender }
}
