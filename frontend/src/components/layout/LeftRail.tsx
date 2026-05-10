import React, { useState } from 'react'
import { SyncPanel } from './SyncPanel'
import { VisualBriefPanel } from './VisualBriefPanel'
import { QualityWarningsPanel } from './QualityWarningsPanel'
import { ChatPanel } from './ChatPanel'
import { SnapshotsPanel } from './SnapshotsPanel'
import { SectionsPanel } from './SectionsPanel'
import type { Campaign, Product, VisualBrief, Section } from '../../lib/api'
import type { ChatCommand } from '../../hooks/useChat'

interface LeftRailProps {
  campaign: Campaign
  onCampaignUpdated: (updated: Campaign) => void
  onSyncComplete?: () => void
  products?: Product[]
  onProductUpdated?: (updated: Product) => void
  brief?: VisualBrief | null
  isBriefLoading?: boolean
  onVibeShift?: () => void
  onOverrideTheme?: () => void
  sections?: Section[]
  onSectionsUpdated?: (sections: Section[]) => void
  onCommandApply?: (commands: ChatCommand[]) => void
  onSnapshotRestored?: (snapshotId: string) => void
}

export function LeftRail({
  campaign,
  onCampaignUpdated,
  onSyncComplete,
  products = [],
  onProductUpdated,
  brief = null,
  isBriefLoading = false,
  onVibeShift,
  onOverrideTheme,
  sections = [],
  onSectionsUpdated,
  onCommandApply,
  onSnapshotRestored,
}: LeftRailProps) {
  const [localSections, setLocalSections] = useState<Section[]>(sections)

  // Sync external sections to local state
  React.useEffect(() => {
    setLocalSections(sections)
  }, [sections])

  const lockedSectionIds = localSections.filter((s) => s.locked).map((s) => s.id)

  const handleSectionsUpdated = (updated: Section[]) => {
    setLocalSections(updated)
    onSectionsUpdated?.(updated)
  }

  return (
    <aside
      className="w-left-rail flex-shrink-0 flex flex-col bg-neutral-50 border-r border-neutral-200 overflow-y-auto"
      aria-label="Campaign settings"
    >
      <SyncPanel
        campaignId={campaign.id}
        sheetUrl={campaign.sheet_url || undefined}
        onSyncComplete={onSyncComplete}
      />
      <VisualBriefPanel
        brief={brief}
        isLoading={isBriefLoading}
        onVibeShift={onVibeShift ?? (() => {})}
        onOverrideTheme={onOverrideTheme ?? (() => {})}
      />
      <SectionsPanel
        campaignId={campaign.id}
        sections={localSections}
        onSectionsUpdated={handleSectionsUpdated}
      />
      <ChatPanel
        campaignId={campaign.id}
        lockedSectionIds={lockedSectionIds}
        onCommandApply={onCommandApply ?? (() => {})}
      />
      <SnapshotsPanel
        campaignId={campaign.id}
        onRestoreSnapshot={onSnapshotRestored ?? (() => {})}
      />
      {onProductUpdated && (
        <QualityWarningsPanel
          campaignId={campaign.id}
          products={products}
          onProductUpdated={onProductUpdated}
        />
      )}
    </aside>
  )
}
