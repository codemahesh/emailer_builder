import React, { useState, useEffect, useCallback } from 'react'
import { Button } from '../ui/Button'
import { showToast } from '../ui/Toast'
import { api } from '../../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Template {
  id: string
  name: string
  source: 'ai' | 'designer'
  structural_pattern: string | null
}

interface TemplatePickerDrawerProps {
  campaignId: string
  isOpen: boolean
  onClose: () => void
  onApply: (template: Template) => void
}

type FilterTab = 'all' | 'ai' | 'saved'

// ── Sub-components ────────────────────────────────────────────────────────────

function SkeletonTile() {
  return (
    <div
      className="h-16 rounded-md bg-neutral-100"
      style={{
        backgroundImage:
          'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
        backgroundSize: '200% 100%',
      }}
    />
  )
}

interface SourcePillProps {
  source: 'ai' | 'designer'
}

function SourcePill({ source }: SourcePillProps) {
  if (source === 'ai') {
    return (
      <span
        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-caption font-medium"
        style={{ backgroundColor: '#EDE4FF', color: '#7B3FE4' }}
      >
        ✦ AI
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-caption font-medium bg-success-50 text-success-600">
      ✋ Saved
    </span>
  )
}

interface TemplateTileProps {
  template: Template
  isSelected: boolean
  onSelect: () => void
}

function TemplateTile({ template, isSelected, onSelect }: TemplateTileProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        'flex items-center justify-between gap-2 w-full rounded-md px-3 py-2.5 text-left',
        'transition-all duration-[160ms]',
        'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1',
        isSelected
          ? 'bg-brand-primary-soft border-2 border-brand-primary'
          : 'bg-neutral-0 border border-neutral-200 hover:border-neutral-400',
      ].join(' ')}
      aria-label={`Select template: ${template.name}`}
      aria-pressed={isSelected}
    >
      <span className="text-small-strong text-neutral-800 truncate flex-1">{template.name}</span>
      <div className="flex items-center gap-2 flex-shrink-0">
        <SourcePill source={template.source} />
        {isSelected && (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path
              d="M2.5 7l3 3 6-6"
              stroke="#2E5BFF"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </div>
    </button>
  )
}

// ── Save-as dialog ────────────────────────────────────────────────────────────

interface SaveAsDialogProps {
  campaignId: string
  onSaved: () => void
  onClose: () => void
}

function SaveAsDialog({ campaignId, onSaved, onClose }: SaveAsDialogProps) {
  const [name, setName] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    if (!name.trim()) return
    setIsSaving(true)
    try {
      await api.post(`/campaigns/${campaignId}/templates/save`, {
        name: name.trim(),
      })
      showToast(`Template "${name.trim()}" saved`, 'success')
      onSaved()
      onClose()
    } catch {
      showToast('Failed to save template', 'error')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Save as template"
    >
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-[360px] mx-4 bg-neutral-0 rounded-lg shadow-elev-modal p-6 flex flex-col gap-4">
        <h3 className="text-heading-3 text-neutral-800">Save as template</h3>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Template name…"
          className={[
            'w-full h-9 px-3 rounded-md border border-neutral-200 text-body text-neutral-800',
            'placeholder:text-neutral-400 bg-neutral-0',
            'focus:outline-none focus:border-brand-primary focus-visible:ring-2 focus-visible:ring-brand-primary',
          ].join(' ')}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSave()
            if (e.key === 'Escape') onClose()
          }}
          autoFocus
        />
        <div className="flex gap-3 justify-end">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!name.trim() || isSaving}
            isLoading={isSaving}
            onClick={handleSave}
          >
            Save
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function TemplatePickerDrawer({
  campaignId,
  isOpen,
  onClose,
  onApply,
}: TemplatePickerDrawerProps) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all')
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [isApplying, setIsApplying] = useState(false)
  const [showSaveAs, setShowSaveAs] = useState(false)

  const fetchTemplates = useCallback(async () => {
    setIsLoading(true)
    setHasError(false)
    try {
      const response = await api.get<Template[]>('/templates')
      setTemplates(response.data)
    } catch {
      setHasError(true)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      fetchTemplates()
    }
  }, [isOpen, fetchTemplates])

  // Esc to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !showSaveAs) onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose, showSaveAs])

  const filteredTemplates = templates.filter((t) => {
    if (activeFilter === 'ai') return t.source === 'ai'
    if (activeFilter === 'saved') return t.source === 'designer'
    return true
  })

  const recommended = filteredTemplates.slice(0, 3)
  const allTemplates = filteredTemplates

  const handleApply = async () => {
    if (!selectedTemplateId) return
    const template = templates.find((t) => t.id === selectedTemplateId)
    if (!template) return

    setIsApplying(true)
    try {
      await api.post(`/campaigns/${campaignId}/templates/apply`, {
        template_id: selectedTemplateId,
      })
      onApply(template)
      showToast(`Template "${template.name}" applied`, 'success')
      onClose()
    } catch {
      showToast('Failed to apply template', 'error')
    } finally {
      setIsApplying(false)
    }
  }

  const tabClasses = (tab: FilterTab) =>
    [
      'px-3 py-1.5 text-small-strong rounded-md transition-colors duration-[160ms]',
      'focus-visible:ring-2 focus-visible:ring-brand-primary',
      activeFilter === tab
        ? 'bg-brand-primary-soft text-brand-primary'
        : 'text-neutral-600 hover:bg-neutral-100',
    ].join(' ')

  return (
    <>
      {/* Scrim */}
      <div
        className={[
          'fixed inset-0 z-40 bg-black/40 transition-opacity duration-[240ms]',
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none',
        ].join(' ')}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        className={[
          'fixed top-0 right-0 bottom-0 z-50 w-[480px] bg-neutral-0 shadow-elev-overlay',
          'flex flex-col transition-transform duration-[240ms]',
          isOpen ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
        role="dialog"
        aria-modal="true"
        aria-label="Choose template"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 flex-shrink-0">
          <h2 className="text-heading-2 text-neutral-800">Choose template</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors duration-[160ms] focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            aria-label="Close template picker"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M15 5L5 15M5 5l10 10"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 px-6 py-3 border-b border-neutral-200 flex-shrink-0">
          {(['all', 'ai', 'saved'] as FilterTab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveFilter(tab)}
              className={tabClasses(tab)}
              aria-pressed={activeFilter === tab}
            >
              {tab === 'all' ? 'All' : tab === 'ai' ? 'AI' : 'Saved'}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-6">
          {/* Error */}
          {hasError && (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-body text-neutral-600">Failed to load templates</p>
              <Button variant="secondary" size="sm" onClick={fetchTemplates}>
                Retry
              </Button>
            </div>
          )}

          {/* Loading */}
          {isLoading && !hasError && (
            <div className="flex flex-col gap-2" aria-busy="true">
              {[...Array(6)].map((_, i) => (
                <SkeletonTile key={i} />
              ))}
            </div>
          )}

          {!isLoading && !hasError && (
            <>
              {/* Recommended rail */}
              {recommended.length > 0 && (
                <div className="flex flex-col gap-2">
                  <p className="text-small-strong text-neutral-600">
                    Recommended for this campaign
                  </p>
                  <div className="flex flex-col gap-2">
                    {recommended.map((t) => (
                      <TemplateTile
                        key={t.id}
                        template={t}
                        isSelected={selectedTemplateId === t.id}
                        onSelect={() => setSelectedTemplateId(t.id)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* All templates */}
              {allTemplates.length > 0 && (
                <div className="flex flex-col gap-2">
                  <p className="text-small-strong text-neutral-600">All templates</p>
                  <div className="flex flex-col gap-2">
                    {allTemplates.map((t) => (
                      <TemplateTile
                        key={t.id}
                        template={t}
                        isSelected={selectedTemplateId === t.id}
                        onSelect={() => setSelectedTemplateId(t.id)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Empty */}
              {allTemplates.length === 0 && (
                <p className="text-small text-neutral-400 italic text-center mt-8">
                  No templates found.
                </p>
              )}

              {/* Save current as template */}
              <button
                type="button"
                onClick={() => setShowSaveAs(true)}
                className="text-small text-brand-primary hover:underline text-left focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
              >
                Save current layout as template…
              </button>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-200 flex gap-3 justify-end flex-shrink-0">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!selectedTemplateId || isApplying}
            isLoading={isApplying}
            onClick={handleApply}
          >
            Apply template
          </Button>
        </div>
      </aside>

      {/* Save-as dialog */}
      {showSaveAs && (
        <SaveAsDialog
          campaignId={campaignId}
          onSaved={fetchTemplates}
          onClose={() => setShowSaveAs(false)}
        />
      )}
    </>
  )
}
