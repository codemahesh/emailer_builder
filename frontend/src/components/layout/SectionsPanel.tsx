import React, { useState } from 'react'
import { toggleSectionLock, type Section } from '../../lib/api'
import { showToast } from '../ui/Toast'

interface SectionsPanelProps {
  campaignId: string
  sections: Section[]
  onSectionsUpdated: (sections: Section[]) => void
}

function LockIcon({ locked }: { locked: boolean }) {
  return locked ? (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <rect x="3" y="6" width="8" height="6" rx="1" stroke="currentColor" strokeWidth="1.25" />
      <path d="M4.5 6V4.5a2.5 2.5 0 0 1 5 0V6" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
    </svg>
  ) : (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <rect x="3" y="6" width="8" height="6" rx="1" stroke="currentColor" strokeWidth="1.25" />
      <path d="M4.5 6V4.5a2.5 2.5 0 0 1 5 0" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
    </svg>
  )
}

export function SectionsPanel({ campaignId, sections, onSectionsUpdated }: SectionsPanelProps) {
  const [togglingId, setTogglingId] = useState<string | null>(null)
  const lockedCount = sections.filter((s) => s.locked).length

  if (sections.length === 0) return null

  const handleToggleLock = async (section: Section) => {
    if (togglingId) return
    setTogglingId(section.id)
    try {
      const updated = await toggleSectionLock(campaignId, section.id, !section.locked)
      onSectionsUpdated(sections.map((s) => (s.id === section.id ? updated : s)))
    } catch {
      showToast('Failed to update section lock', 'error')
    } finally {
      setTogglingId(null)
    }
  }

  return (
    <div className="border-t border-neutral-200">
      {/* Panel header */}
      <div className="px-4 py-3 flex items-center justify-between">
        <span className="text-small-strong uppercase tracking-wider text-neutral-600">Sections</span>
        {lockedCount > 0 && (
          <span className="text-caption text-neutral-400">
            {lockedCount} locked
          </span>
        )}
      </div>

      {/* Section list */}
      <ul className="flex flex-col">
        {sections.map((section) => (
          <li
            key={section.id}
            className={[
              'flex items-center gap-2 px-4 py-2 group',
              section.locked ? 'border-l-2 border-l-brand-primary' : 'border-l-2 border-l-transparent',
            ].join(' ')}
          >
            {/* Lock/unlock button */}
            <button
              type="button"
              onClick={() => handleToggleLock(section)}
              disabled={togglingId === section.id}
              title={
                section.locked
                  ? 'Locked: AI will not modify. Fast Sync still updates prices.'
                  : 'Click to lock this section'
              }
              aria-label={section.locked ? `Unlock section: ${section.title}` : `Lock section: ${section.title}`}
              aria-pressed={section.locked}
              className={[
                'flex-shrink-0 w-6 h-6 flex items-center justify-center rounded transition-colors duration-[160ms]',
                'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1',
                section.locked
                  ? 'text-brand-primary hover:text-brand-primary-hover'
                  : 'text-neutral-300 hover:text-neutral-600 opacity-0 group-hover:opacity-100',
                togglingId === section.id ? 'opacity-50 cursor-not-allowed' : '',
              ].join(' ')}
            >
              <LockIcon locked={section.locked} />
            </button>

            {/* Section title */}
            <span
              className={[
                'flex-1 text-small truncate',
                section.locked ? 'text-neutral-800' : 'text-neutral-600',
              ].join(' ')}
            >
              {section.title}
            </span>

            {/* Position badge */}
            <span className="text-caption text-neutral-400 flex-shrink-0">
              {section.position + 1}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
