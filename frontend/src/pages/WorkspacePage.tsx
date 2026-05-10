import React, { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getCampaign,
  getProducts,
  getVisualBrief,
  getSections,
  getBanners,
  getThemes,
  getTemplates,
  applyTheme,
  applyTemplate,
  applyAssetOverride,
  createReviewToken,
  recordPreferenceSignal,
  type Campaign,
  type Product,
  type VisualBrief,
  type Section,
  type Banner,
  type ImageProcessingProgress,
} from '../lib/api'
import type { ChatCommand } from '../hooks/useChat'
import { TopBar } from '../components/layout/TopBar'
import { LeftRail } from '../components/layout/LeftRail'
import { Skeleton } from '../components/ui/Skeleton'
import { showToast } from '../components/ui/Toast'
import { useWebSocket } from '../hooks/useWebSocket'
import { useRender } from '../hooks/useRender'
import { PreviewPane } from '../components/PreviewPane'
import { VibeShiftModal } from '../components/modals/VibeShiftModal'
import { SharePanel } from '../components/modals/SharePanel'
import { ExportDrawer } from '../components/drawers/ExportDrawer'
import { ThemePickerDrawer } from '../components/drawers/ThemePickerDrawer'
import { TemplatePickerDrawer } from '../components/drawers/TemplatePickerDrawer'
import { KeyboardShortcutsOverlay } from '../components/ui/KeyboardShortcutsOverlay'

// ── Skeleton ──────────────────────────────────────────────────────────────────

function WorkspaceSkeleton() {
  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left rail skeleton */}
      <div className="w-left-rail flex-shrink-0 bg-neutral-50 border-r border-neutral-200 p-4 flex flex-col gap-4">
        <Skeleton className="w-2/3 h-5" />
        <Skeleton className="w-full h-16 rounded-md" />
        <Skeleton className="w-full h-9" />
        <Skeleton className="w-full h-9 mt-2" />
      </div>
      {/* Preview skeleton */}
      <div className="flex-1 bg-neutral-100 flex items-center justify-center">
        <div className="text-center flex flex-col items-center gap-3">
          <Skeleton className="w-14 h-14 rounded-2xl" />
          <Skeleton className="w-56 h-5" />
          <Skeleton className="w-40 h-4" />
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function WorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [brief, setBrief] = useState<VisualBrief | null>(null)
  const [isBriefLoading, setIsBriefLoading] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const [sections, setSections] = useState<Section[]>([])
  const [banners, setBanners] = useState<Banner[]>([])
  const [vibeShiftOpen, setVibeShiftOpen] = useState(false)
  const [sharePanelOpen, setSharePanelOpen] = useState(false)
  const [reviewUrl, setReviewUrl] = useState('')
  const [exportDrawerOpen, setExportDrawerOpen] = useState(false)
  const [themePickerOpen, setThemePickerOpen] = useState(false)
  const [templatePickerOpen, setTemplatePickerOpen] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  // Render state via useRender hook
  const { html: renderHtml, renderResult, isRendering, render: fetchRender, triggerRender } = useRender(id)

  // ── Data loading ────────────────────────────────────────────────────────────

  const loadCampaign = useCallback(
    async (campaignId: string) => {
      try {
        const data = await getCampaign(campaignId)
        setCampaign(data)
        return data
      } catch (err: unknown) {
        const e = err as { response?: { status?: number } }
        if (e?.response?.status === 404) {
          setNotFound(true)
        } else {
          showToast('Failed to load campaign', 'error')
          navigate('/campaigns')
        }
        return null
      }
    },
    [navigate],
  )

  const loadProducts = useCallback(async (campaignId: string) => {
    try {
      const data = await getProducts(campaignId)
      setProducts(data)
      return data
    } catch {
      return []
    }
  }, [])

  const loadSections = useCallback(async (campaignId: string) => {
    try {
      const data = await getSections(campaignId)
      setSections(data)
    } catch {
      // sections are optional enrichment
    }
  }, [])

  const loadBanners = useCallback(async (campaignId: string) => {
    try {
      const data = await getBanners(campaignId)
      setBanners(data)
    } catch {
      // banners are optional
    }
  }, [])

  const loadBrief = useCallback(async (campaignId: string) => {
    setIsBriefLoading(true)
    try {
      const data = await getVisualBrief(campaignId)
      setBrief(data)
    } catch (err: unknown) {
      const e = err as { response?: { status?: number } }
      // 404 = no brief yet (pre-sync state) — not an error
      if (e?.response?.status !== 404) {
        setBrief(null)
      }
    } finally {
      setIsBriefLoading(false)
    }
  }, [])

  // ── Initial load ────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!id) return
    const load = async () => {
      setIsLoading(true)
      const data = await loadCampaign(id)
      if (data) {
        await Promise.all([loadProducts(id), loadBrief(id), fetchRender(), loadSections(id), loadBanners(id)])
      }
      setIsLoading(false)
    }
    load()
  }, [id, loadCampaign, loadProducts, loadBrief, fetchRender, loadSections, loadBanners])

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleSyncComplete = useCallback(async () => {
    if (!id) return
    await loadCampaign(id)
    await loadProducts(id)
    // Refresh brief — orchestrator runs after sync and may have produced a new one
    await loadBrief(id)
    await loadSections(id)
    triggerRender()
  }, [id, loadCampaign, loadProducts, loadBrief, loadSections, triggerRender])

  const handleProductUpdated = useCallback(
    (updatedProduct: Product) => {
      setProducts((prev) => {
        const next = prev.map((p) => (p.id === updatedProduct.id ? updatedProduct : p))
        // Debounce re-render when products change
        triggerRender()
        return next
      })
    },
    [triggerRender],
  )

  // ── Keyboard shortcut: Shift+/ → shortcuts overlay ────────────────────────
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.shiftKey && e.key === '/') setShortcutsOpen(true)
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [])

  const handleShare = useCallback(async () => {
    if (!id) return
    try {
      const token = await createReviewToken(id)
      const url = `${window.location.origin}/preview/${token.token}`
      setReviewUrl(url)
      setSharePanelOpen(true)
    } catch {
      showToast('Failed to create review link', 'error')
    }
  }, [id])

  const handleExport = useCallback(() => {
    setExportDrawerOpen(true)
  }, [])

  // ── Issue 17: Banner thumb feedback → preference signal ──────────────────────
  const handleBannerFeedback = useCallback(
    async (bannerId: string, vote: 'up' | 'down') => {
      const banner = banners.find((b) => b.id === bannerId)
      if (!banner) return
      try {
        await recordPreferenceSignal({
          signal_type: vote === 'up' ? 'explicit_positive' : 'explicit_negative',
          asset_type: 'hero_banner',
          signal_value: `variant_${banner.variant_index}`,
          campaign_id: id,
        })
      } catch {
        // preference signals are non-critical
      }
    },
    [banners, id],
  )

  // ── Issue 14: Chat command dispatch ──────────────────────────────────────────
  const handleCommandApply = useCallback(
    async (commands: ChatCommand[]) => {
      if (!id) return
      let needsBriefReload = false

      for (const cmd of commands) {
        try {
          if (cmd.action === 'apply_theme_by_name') {
            const name = cmd.params.name as string
            const themes = await getThemes()
            const theme = themes.find((t) => t.name.toLowerCase() === name?.toLowerCase())
            if (theme) {
              await applyTheme(id, theme.id)
              needsBriefReload = true
            } else {
              showToast(`Theme "${name}" not found`, 'error')
            }
          } else if (cmd.action === 'apply_template_by_name') {
            const name = cmd.params.name as string
            const templates = await getTemplates()
            const tpl = templates.find((t) => t.name.toLowerCase() === name?.toLowerCase())
            if (tpl) {
              await applyTemplate(id, tpl.id)
              needsBriefReload = true
            } else {
              showToast(`Template "${name}" not found`, 'error')
            }
          } else if (cmd.action === 'replace_asset') {
            const { target_type, target_id, url } = cmd.params as {
              target_type: string
              target_id?: string
              url: string
            }
            await applyAssetOverride(id, { target_type, target_id, override_url: url })
          }
          // reorder_section, swap_products, apply_design_token: re-render is sufficient
          // since backend will apply these via the render route reading current state
        } catch {
          showToast(`Failed to apply command: ${cmd.action}`, 'error')
        }
      }

      if (needsBriefReload) {
        await loadBrief(id)
      }
      triggerRender()
    },
    [id, loadBrief, triggerRender],
  )

  // ── WebSocket: real-time image processing progress ─────────────────────────
  const handleWsMessage = useCallback(
    (msg: ImageProcessingProgress) => {
      if (msg.type === 'image_processed' && msg.data.product_id) {
        const { product_id, url, verdict } = msg.data
        setProducts((prev) => {
          const next = prev.map((p) => {
            if (p.id !== product_id) return p
            return {
              ...p,
              ...(url ? { processed_image_url: url } : {}),
              ...(verdict === 'fail' ? { scrape_failed: true } : {}),
            }
          })
          // Debounce re-render after image update
          triggerRender()
          return next
        })
      }
    },
    [triggerRender],
  )

  useWebSocket(id, handleWsMessage)

  // ── Render ──────────────────────────────────────────────────────────────────

  if (notFound) {
    return (
      <div className="min-h-screen flex flex-col bg-neutral-50">
        <TopBar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-heading-1 text-neutral-800 mb-2">Campaign not found</h2>
            <p className="text-body text-neutral-400 mb-6">
              This campaign doesn't exist or you don't have access to it.
            </p>
            <button
              type="button"
              className="text-brand-primary text-body-strong hover:underline"
              onClick={() => navigate('/campaigns')}
            >
              Back to campaigns
            </button>
          </div>
        </div>
      </div>
    )
  }

  const breadcrumbs = campaign
    ? [
        { label: 'Campaigns', href: '/campaigns' },
        { label: campaign.name },
      ]
    : [{ label: 'Campaigns', href: '/campaigns' }, { label: '…' }]

  return (
    <div className="min-h-screen flex flex-col bg-neutral-50 overflow-hidden">
      <TopBar
        breadcrumbs={breadcrumbs}
        campaignStatus={campaign?.status}
        qualityWarningCount={products.filter((p) => p.scrape_failed).length}
      />

      {isLoading || !campaign ? (
        <WorkspaceSkeleton />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <LeftRail
            campaign={campaign}
            onCampaignUpdated={(updated) => setCampaign(updated)}
            onSyncComplete={handleSyncComplete}
            products={products}
            onProductUpdated={handleProductUpdated}
            brief={brief}
            isBriefLoading={isBriefLoading}
            onVibeShift={() => setVibeShiftOpen(true)}
            onOverrideTheme={() => setThemePickerOpen(true)}
            sections={sections}
            onSectionsUpdated={(updated) => setSections(updated)}
            onCommandApply={handleCommandApply}
            onSnapshotRestored={() => {
              if (id) {
                loadCampaign(id)
                loadProducts(id)
                loadBrief(id)
                triggerRender()
              }
            }}
          />
          <PreviewPane
            campaignId={campaign.id}
            renderHtml={renderHtml ?? null}
            renderSizeKb={renderResult?.size_kb ?? 0}
            sectionCount={renderResult?.section_count ?? 0}
            productCount={renderResult?.product_count ?? 0}
            isLoading={isRendering}
            onShare={handleShare}
            onExport={handleExport}
            banners={banners}
            onBannerActivated={(bannerId) => {
              setBanners((prev) =>
                prev.map((b) => ({ ...b, is_active: b.id === bannerId }))
              )
            }}
            onBannerFeedback={handleBannerFeedback}
          />
        </div>
      )}

      {/* ── Modals & Drawers ──────────────────────────────────────────────── */}
      {campaign && (
        <>
          <SharePanel
            isOpen={sharePanelOpen}
            onClose={() => setSharePanelOpen(false)}
            reviewUrl={reviewUrl}
            campaign={campaign}
            onCampaignUpdated={(updated) => setCampaign(updated)}
          />

          <VibeShiftModal
            campaignId={campaign.id}
            isOpen={vibeShiftOpen}
            onClose={() => setVibeShiftOpen(false)}
            onConfirm={() => {
              setVibeShiftOpen(false)
              if (id) loadBrief(id).then(() => triggerRender())
            }}
          />

          <ExportDrawer
            campaignId={campaign.id}
            isOpen={exportDrawerOpen}
            onClose={() => setExportDrawerOpen(false)}
          />

          <ThemePickerDrawer
            campaignId={campaign.id}
            isOpen={themePickerOpen}
            onClose={() => setThemePickerOpen(false)}
            onApply={() => {
              setThemePickerOpen(false)
              if (id) loadBrief(id).then(() => triggerRender())
            }}
          />

          <TemplatePickerDrawer
            campaignId={campaign.id}
            isOpen={templatePickerOpen}
            onClose={() => setTemplatePickerOpen(false)}
            onApply={() => {
              setTemplatePickerOpen(false)
              if (id) loadBrief(id).then(() => triggerRender())
            }}
          />
        </>
      )}

      <KeyboardShortcutsOverlay
        isOpen={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
    </div>
  )
}
