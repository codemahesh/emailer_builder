import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import {
  listCampaigns,
  createCampaign,
  duplicateCampaign,
  archiveCampaign,
  uploadSheetFile,
  startFullSync,
  getSyncStatus,
  type Campaign,
  type CampaignStatus,
} from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Modal } from '../components/ui/Modal'
import { StatusPill } from '../components/ui/Pill'
import { CampaignCardSkeleton } from '../components/ui/Skeleton'
import { showToast } from '../components/ui/Toast'
import { TopBar } from '../components/layout/TopBar'

type FilterTab = 'all' | CampaignStatus

const filterTabs: { label: string; value: FilterTab }[] = [
  { label: 'All', value: 'all' },
  { label: 'Draft', value: 'draft' },
  { label: 'In Review', value: 'in_review' },
  { label: 'Approved', value: 'approved' },
]

// ─── Campaign Card ────────────────────────────────────────────────────────────

interface CampaignCardProps {
  campaign: Campaign
  onClick: () => void
  onDuplicated: (newCampaign: Campaign) => void
  onArchived: (campaignId: string) => void
}

function OverflowMenu({
  onDuplicate,
  onArchive,
  isDuplicating = false,
  isArchiving = false,
}: {
  onDuplicate: () => void
  onArchive: () => void
  isDuplicating?: boolean
  isArchiving?: boolean
}) {
  const [open, setOpen] = useState(false)
  const ref = React.useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          setOpen((v) => !v)
        }}
        className="w-7 h-7 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors text-body-strong"
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="More options"
      >
        ⋯
      </button>
      {open && (
        <div className="absolute right-0 top-8 w-40 bg-neutral-0 rounded-lg shadow-elev-overlay border border-neutral-100 overflow-hidden z-10">
          <button
            type="button"
            disabled={isDuplicating}
            className="w-full text-left px-4 py-2 text-body text-neutral-800 hover:bg-neutral-50 transition-colors disabled:opacity-50"
            onClick={(e) => {
              e.stopPropagation()
              setOpen(false)
              onDuplicate()
            }}
          >
            {isDuplicating ? 'Duplicating…' : 'Duplicate'}
          </button>
          <button
            type="button"
            disabled={isArchiving}
            className="w-full text-left px-4 py-2 text-body text-danger-600 hover:bg-danger-50 transition-colors disabled:opacity-50"
            onClick={(e) => {
              e.stopPropagation()
              setOpen(false)
              onArchive()
            }}
          >
            {isArchiving ? 'Archiving…' : 'Archive'}
          </button>
        </div>
      )}
    </div>
  )
}

function CampaignCard({ campaign, onClick, onDuplicated, onArchived }: CampaignCardProps) {
  const [isDuplicating, setIsDuplicating] = useState(false)
  const [isArchiving, setIsArchiving] = useState(false)
  const updatedAgo = formatDistanceToNow(new Date(campaign.updated_at), {
    addSuffix: true,
  })
  const ownerLabel = campaign.owner?.email?.split('@')[0] ?? 'unknown'

  const handleDuplicate = async () => {
    setIsDuplicating(true)
    try {
      const newCampaign = await duplicateCampaign(campaign.id)
      onDuplicated(newCampaign)
      showToast(`"${newCampaign.name}" created`, 'success')
    } catch {
      showToast('Failed to duplicate campaign', 'error')
    } finally {
      setIsDuplicating(false)
    }
  }

  const handleArchive = async () => {
    setIsArchiving(true)
    try {
      await archiveCampaign(campaign.id)
      onArchived(campaign.id)
      showToast('Campaign archived', 'info')
    } catch {
      showToast('Failed to archive campaign', 'error')
    } finally {
      setIsArchiving(false)
    }
  }

  return (
    <article
      className="flex flex-col rounded-lg border border-neutral-200 bg-neutral-0 shadow-elev-flat hover:shadow-elev-raised transition-shadow duration-200 cursor-pointer min-h-[240px] overflow-hidden"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
      aria-label={`Open campaign: ${campaign.name}`}
    >
      {/* Thumbnail */}
      <div className="h-[160px] bg-neutral-100 flex items-center justify-center flex-shrink-0 border-b border-neutral-100">
        <svg
          width="40"
          height="40"
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="text-neutral-300"
        >
          <rect x="4" y="8" width="32" height="24" rx="4" stroke="currentColor" strokeWidth="2" />
          <path d="M4 16H36" stroke="currentColor" strokeWidth="2" />
          <path d="M12 24H28" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <path d="M12 28.5H21" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      </div>

      {/* Body */}
      <div className="flex flex-col flex-1 p-4 gap-2">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-body-strong text-neutral-800 line-clamp-2 flex-1 min-w-0">
            {campaign.name}
          </h3>
          <OverflowMenu
            onDuplicate={handleDuplicate}
            onArchive={handleArchive}
            isDuplicating={isDuplicating}
            isArchiving={isArchiving}
          />
        </div>

        <StatusPill status={campaign.status} />

        <p className="text-small text-neutral-400 mt-auto">
          Edited {updatedAgo} · {ownerLabel}
        </p>
      </div>
    </article>
  )
}

// ─── New Campaign Modal ───────────────────────────────────────────────────────

type ModalStep = 'form' | 'syncing' | 'error'
type ImportSource = 'link' | 'upload'

interface NewCampaignModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: (campaign: Campaign) => void
}

function NewCampaignModal({ isOpen, onClose, onCreated }: NewCampaignModalProps) {
  const navigate = useNavigate()
  const [step, setStep] = useState<ModalStep>('form')
  const [source, setSource] = useState<ImportSource>('link')
  const [name, setName] = useState('')
  const [sheetUrl, setSheetUrl] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [syncMessage, setSyncMessage] = useState('')
  const [syncProgress, setSyncProgress] = useState({ processed: 0, total: 0 })
  const [errorMsg, setErrorMsg] = useState('')
  const [campaignCreated, setCampaignCreated] = useState(false)
  const [copied, setCopied] = useState(false)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const campaignIdRef = useRef('')
  const syncStartRef = useRef(0)

  const serviceAccountEmail =
    ((import.meta as unknown as { env: Record<string, string> }).env.VITE_SERVICE_ACCOUNT_EMAIL) ??
    'emailer-builder@your-project.iam.gserviceaccount.com'

  const isValid =
    name.trim().length > 0 &&
    (source === 'link' ? sheetUrl.trim().length > 0 : selectedFile !== null)

  const stopPoll = () => {
    if (pollRef.current) { clearTimeout(pollRef.current); pollRef.current = null }
  }

  const resetForm = () => {
    stopPoll()
    setStep('form')
    setSource('link')
    setName('')
    setSheetUrl('')
    setSelectedFile(null)
    setSyncMessage('')
    setSyncProgress({ processed: 0, total: 0 })
    setErrorMsg('')
    setCampaignCreated(false)
    campaignIdRef.current = ''
    syncStartRef.current = 0
  }

  const handleClose = () => {
    if (step === 'syncing') return
    resetForm()
    onClose()
  }

  const handleCopyEmail = async () => {
    await navigator.clipboard.writeText(serviceAccountEmail)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  useEffect(() => { return () => stopPoll() }, [])

  const pollSyncStatus = (cid: string) => {
    const elapsed = Date.now() - syncStartRef.current
    if (elapsed > 180_000) {
      stopPoll()
      navigate(`/campaigns/${cid}`)
      return
    }
    getSyncStatus(cid)
      .then((status) => {
        const s = status.status
        if (s === 'completed' || s === 'partial') {
          stopPoll()
          navigate(`/campaigns/${cid}/review`)
        } else if (s === 'failed') {
          stopPoll()
          setErrorMsg('Sync failed. You can continue to the workspace to retry.')
          setStep('error')
        } else {
          if (status.total > 0) {
            setSyncProgress({ processed: status.processed, total: status.total })
            setSyncMessage(`Processing products… ${status.processed} / ${status.total}`)
          }
          pollRef.current = setTimeout(() => pollSyncStatus(cid), 1500)
        }
      })
      .catch(() => {
        pollRef.current = setTimeout(() => pollSyncStatus(cid), 3000)
      })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid || step === 'syncing') return

    setStep('syncing')
    setSyncMessage('Creating campaign…')

    try {
      const campaign = await createCampaign({
        name: name.trim(),
        sheet_url: source === 'link' ? sheetUrl.trim() : undefined,
      })
      campaignIdRef.current = campaign.id
      setCampaignCreated(true)
      onCreated(campaign)

      if (source === 'upload') {
        setSyncMessage('Importing products…')
        const result = await uploadSheetFile(campaign.id, selectedFile!)
        if (!result.ok) {
          setErrorMsg(
            result.error_code === 'MISSING_COLUMNS'
              ? 'File is missing required columns (sku, product_link). Please fix and try again.'
              : 'Could not import the file. Please check the format and try again.',
          )
          setStep('error')
          return
        }
        navigate(`/campaigns/${campaign.id}/review`)
      } else {
        setSyncMessage('Starting sync…')
        await startFullSync(campaign.id)
        syncStartRef.current = Date.now()
        pollRef.current = setTimeout(() => pollSyncStatus(campaign.id), 1500)
      }
    } catch {
      if (!campaignIdRef.current) {
        setErrorMsg('Failed to create campaign. Please try again.')
      } else {
        setErrorMsg('Campaign created but sync could not start. Go to the workspace to retry.')
      }
      setStep('error')
    }
  }

  const handleGoToWorkspace = () => {
    const cid = campaignIdRef.current
    stopPoll()
    onClose()
    if (cid) navigate(`/campaigns/${cid}`)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={step === 'syncing' ? 'Syncing products…' : 'New Campaign'}
      width="md"
      disableBackdropClose={step === 'syncing'}
    >
      {/* ── Step 1: Form ── */}
      {step === 'form' && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-5 px-6 py-5">
          {/* Source selection */}
          <div className="flex flex-col gap-2">
            <span className="text-body-strong text-neutral-800">Import products from</span>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setSource('link')}
                className={[
                  'flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors',
                  source === 'link'
                    ? 'border-brand-primary bg-brand-primary/5'
                    : 'border-neutral-200 bg-neutral-0 hover:border-neutral-300',
                ].join(' ')}
              >
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="2" y="2" width="24" height="24" rx="4" fill="#34A853" fillOpacity="0.12"/>
                  <rect x="6" y="6" width="16" height="16" rx="1.5" stroke="#34A853" strokeWidth="1.5"/>
                  <line x1="6" y1="11" x2="22" y2="11" stroke="#34A853" strokeWidth="1.25"/>
                  <line x1="6" y1="16" x2="22" y2="16" stroke="#34A853" strokeWidth="1.25"/>
                  <line x1="11" y1="6" x2="11" y2="22" stroke="#34A853" strokeWidth="1.25"/>
                </svg>
                <span className="text-body-strong text-neutral-800">Google Sheet</span>
                <span className="text-small text-neutral-500">Paste a Sheets URL</span>
              </button>
              <button
                type="button"
                onClick={() => setSource('upload')}
                className={[
                  'flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors',
                  source === 'upload'
                    ? 'border-brand-primary bg-brand-primary/5'
                    : 'border-neutral-200 bg-neutral-0 hover:border-neutral-300',
                ].join(' ')}
              >
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="2" y="2" width="24" height="24" rx="4" fill="#2E5BFF" fillOpacity="0.08"/>
                  <path d="M14 18V10M14 10L10.5 13.5M14 10L17.5 13.5" stroke="#2E5BFF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M8 21h12" stroke="#2E5BFF" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                <span className="text-body-strong text-neutral-800">Upload file</span>
                <span className="text-small text-neutral-500">.xlsx or .csv</span>
              </button>
            </div>
          </div>

          {/* Campaign name */}
          <Input
            label="Campaign name"
            placeholder="e.g. Summer 2025 Newsletter"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />

          {/* Source-specific input */}
          {source === 'link' ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 bg-neutral-50 rounded-md px-3 py-2 border border-neutral-200">
                <span className="text-small text-neutral-500 font-mono flex-1 min-w-0 truncate">
                  {serviceAccountEmail}
                </span>
                <button
                  type="button"
                  onClick={handleCopyEmail}
                  className="flex-shrink-0 text-small-strong text-brand-primary hover:text-brand-primary-hover transition-colors"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <p className="text-small text-neutral-500 -mt-1">
                Share your Google Sheet with the above email first.
              </p>
              <Input
                label="Google Sheet URL"
                type="url"
                placeholder="https://docs.google.com/spreadsheets/d/…"
                value={sheetUrl}
                onChange={(e) => setSheetUrl(e.target.value)}
              />
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              <label className="text-body-strong text-neutral-800">File</label>
              <input
                type="file"
                accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                className="text-body text-neutral-800 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-body file:bg-neutral-100 file:text-neutral-800 hover:file:bg-neutral-200 cursor-pointer"
              />
              <p className="text-small text-neutral-400">Must include "sku" and "product_link" columns.</p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 pt-1 border-t border-neutral-100 -mx-6 px-6 pb-1 mt-1">
            <Button type="button" variant="ghost" onClick={handleClose}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={!isValid}>
              Create &amp; Sync
            </Button>
          </div>
        </form>
      )}

      {/* ── Step 2: Syncing ── */}
      {step === 'syncing' && (
        <div className="flex flex-col items-center gap-5 px-6 py-10">
          <div className="w-10 h-10 rounded-full border-[3px] border-brand-primary border-t-transparent animate-spin" />
          <p className="text-body text-neutral-600 text-center">{syncMessage}</p>
          {syncProgress.total > 0 && (
            <div className="w-full flex flex-col gap-1.5">
              <div className="w-full bg-neutral-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-brand-primary h-2 rounded-full transition-all duration-500"
                  style={{ width: `${Math.round((syncProgress.processed / syncProgress.total) * 100)}%` }}
                />
              </div>
              <p className="text-small text-neutral-400 text-center">
                {syncProgress.processed} of {syncProgress.total} products processed
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Step 3: Error ── */}
      {step === 'error' && (
        <div className="flex flex-col items-center gap-5 px-6 py-8">
          <div className="w-10 h-10 rounded-full bg-danger-50 flex items-center justify-center text-danger-600 text-lg font-bold">
            ✕
          </div>
          <p className="text-body text-neutral-700 text-center">{errorMsg}</p>
          <div className="flex gap-3">
            {campaignCreated ? (
              <>
                <Button variant="ghost" onClick={handleClose}>Close</Button>
                <Button variant="primary" onClick={handleGoToWorkspace}>Go to Workspace</Button>
              </>
            ) : (
              <>
                <Button variant="ghost" onClick={handleClose}>Cancel</Button>
                <Button variant="primary" onClick={() => { setStep('form'); setErrorMsg('') }}>Try Again</Button>
              </>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}

// ─── Dashboard Page ───────────────────────────────────────────────────────────

export function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all')
  const [showNewModal, setShowNewModal] = useState(false)

  const fetchCampaigns = useCallback(
    async (filter: FilterTab) => {
      setIsLoading(true)
      try {
        const result = await listCampaigns({
          status: filter === 'all' ? undefined : filter,
        })
        setCampaigns(result.items)
      } catch {
        showToast('Failed to load campaigns', 'error')
      } finally {
        setIsLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    fetchCampaigns(activeFilter)
  }, [activeFilter, fetchCampaigns])

  const handleFilterChange = (filter: FilterTab) => {
    setActiveFilter(filter)
  }

  const handleCampaignCreated = (campaign: Campaign) => {
    setCampaigns(prev => [campaign, ...prev])
  }

  const handleCardClick = (campaignId: string) => {
    navigate(`/campaigns/${campaignId}`)
  }

  const isFirstName = user?.email?.split('@')[0] ?? 'there'

  return (
    <div className="min-h-screen flex flex-col bg-neutral-50">
      <TopBar />

      {/* Dashboard header */}
      <div className="sticky top-0 z-10 bg-neutral-50 border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-[80px]">
            <h1 className="text-heading-1 text-neutral-900">My Campaigns</h1>
            <Button
              variant="primary"
              size="md"
              onClick={() => setShowNewModal(true)}
              leftIcon={
                <span className="text-base leading-none font-bold">+</span>
              }
            >
              New Campaign
            </Button>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1 -mb-px">
            {filterTabs.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => handleFilterChange(tab.value)}
                className={[
                  'px-4 py-2.5 text-body-strong border-b-2 transition-colors duration-150',
                  activeFilter === tab.value
                    ? 'border-brand-primary text-brand-primary'
                    : 'border-transparent text-neutral-600 hover:text-neutral-800 hover:border-neutral-200',
                ].join(' ')}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6">
        {isLoading ? (
          /* Skeleton grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <CampaignCardSkeleton key={i} />
            ))}
          </div>
        ) : campaigns.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-2xl bg-brand-primary-soft flex items-center justify-center mb-6">
              <svg
                width="32"
                height="32"
                viewBox="0 0 32 32"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect
                  x="4"
                  y="6"
                  width="24"
                  height="20"
                  rx="3"
                  stroke="#2E5BFF"
                  strokeWidth="2"
                />
                <path d="M4 13H28" stroke="#2E5BFF" strokeWidth="2" />
                <path
                  d="M10 19H22"
                  stroke="#2E5BFF"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                />
                <path
                  d="M10 23H16"
                  stroke="#2E5BFF"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <h2 className="text-display text-neutral-900 mb-2">
              {activeFilter === 'all'
                ? 'Start your first campaign'
                : `No ${filterTabs.find((t) => t.value === activeFilter)?.label ?? ''} campaigns`}
            </h2>
            <p className="text-body text-neutral-400 max-w-[480px] mb-8">
              {activeFilter === 'all'
                ? `Hi ${isFirstName}! Create a campaign to start building personalised emails at scale using your Google Sheets data.`
                : 'Change the filter or create a new campaign to get started.'}
            </p>
            {activeFilter === 'all' && (
              <Button
                variant="primary"
                size="lg"
                onClick={() => setShowNewModal(true)}
                leftIcon={
                  <span className="text-base leading-none font-bold">+</span>
                }
              >
                New Campaign
              </Button>
            )}
          </div>
        ) : (
          /* Campaign grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {campaigns.map((campaign) => (
              <CampaignCard
                key={campaign.id}
                campaign={campaign}
                onClick={() => handleCardClick(campaign.id)}
                onDuplicated={(newCampaign) => {
                  setCampaigns((prev) => [newCampaign, ...prev])
                }}
                onArchived={(archivedId) => {
                  setCampaigns((prev) => prev.filter((c) => c.id !== archivedId))
                }}
              />
            ))}
          </div>
        )}
      </main>

      <NewCampaignModal
        isOpen={showNewModal}
        onClose={() => setShowNewModal(false)}
        onCreated={handleCampaignCreated}
      />
    </div>
  )
}
