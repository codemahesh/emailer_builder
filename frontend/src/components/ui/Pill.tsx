import React from 'react'
import type { CampaignStatus } from '../../lib/api'

type PillVariant = CampaignStatus | 'ai' | 'manual' | 'scrape' | 'locked' | 'neutral'

interface PillProps {
  variant?: PillVariant
  children: React.ReactNode
  className?: string
}

const variantStyles: Record<PillVariant, string> = {
  draft:     'bg-neutral-100 text-neutral-600',
  in_review: 'bg-warn-50 text-warn-600',
  approved:  'bg-success-50 text-success-600',
  ai:        'bg-purple-50 text-prov-ai',
  manual:    'bg-success-50 text-prov-manual',
  scrape:    'bg-neutral-100 text-prov-scrape',
  locked:    'bg-neutral-800 text-neutral-0',
  neutral:   'bg-neutral-100 text-neutral-600',
}

const statusLabels: Record<CampaignStatus, string> = {
  draft:     'Draft',
  in_review: 'In Review',
  approved:  'Approved',
}

export function Pill({ variant = 'neutral', children, className = '' }: PillProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-small-strong',
        variantStyles[variant],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </span>
  )
}

interface StatusPillProps {
  status: CampaignStatus
  className?: string
}

export function StatusPill({ status, className }: StatusPillProps) {
  return (
    <Pill variant={status} className={className}>
      {statusLabels[status]}
    </Pill>
  )
}
