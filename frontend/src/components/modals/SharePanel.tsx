import React, { useState } from 'react'
import { Modal } from '../ui/Modal'
import { Button } from '../ui/Button'
import { showToast } from '../ui/Toast'
import { updateCampaign, type Campaign, type CampaignStatus } from '../../lib/api'

interface SharePanelProps {
  isOpen: boolean
  onClose: () => void
  reviewUrl: string
  campaign: Campaign
  onCampaignUpdated: (c: Campaign) => void
}

export function SharePanel({ isOpen, onClose, reviewUrl, campaign, onCampaignUpdated }: SharePanelProps) {
  const [copied, setCopied] = useState(false)
  const [isMarkingInReview, setIsMarkingInReview] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(reviewUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      showToast('Review link copied to clipboard', 'success')
    } catch {
      showToast('Failed to copy link', 'error')
    }
  }

  const handleMarkInReview = async () => {
    if (campaign.status === 'in_review') {
      // Revert to draft
      setIsMarkingInReview(true)
      try {
        const updated = await updateCampaign(campaign.id, { status: 'draft' as CampaignStatus })
        onCampaignUpdated(updated)
        showToast('Campaign moved back to Draft', 'info')
      } catch {
        showToast('Failed to update status', 'error')
      } finally {
        setIsMarkingInReview(false)
      }
    } else {
      setIsMarkingInReview(true)
      try {
        const updated = await updateCampaign(campaign.id, { status: 'in_review' as CampaignStatus })
        onCampaignUpdated(updated)
        showToast('Campaign marked as In Review', 'success')
      } catch {
        showToast('Failed to update status', 'error')
      } finally {
        setIsMarkingInReview(false)
      }
    }
  }

  const isInReview = campaign.status === 'in_review'

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Share for Review" width="sm">
      <div className="flex flex-col gap-5 px-6 py-5">
        {/* Review URL */}
        <div className="flex flex-col gap-2">
          <label className="text-small text-neutral-600">Review link</label>
          <div className="flex items-center gap-2 bg-neutral-50 rounded-md px-3 py-2 border border-neutral-200">
            <span className="flex-1 text-small text-neutral-600 font-mono truncate min-w-0">
              {reviewUrl}
            </span>
            <button
              type="button"
              onClick={handleCopy}
              className="flex-shrink-0 text-small-strong text-brand-primary hover:text-brand-primary-hover transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <p className="text-caption text-neutral-400">
            Anyone with this link can view the email preview and leave comments.
          </p>
        </div>

        {/* Mark as In Review toggle */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between p-3 rounded-lg border border-neutral-200 bg-neutral-0">
            <div className="flex flex-col gap-0.5">
              <span className="text-small-strong text-neutral-800">Mark as In Review</span>
              <span className="text-caption text-neutral-400">
                {isInReview
                  ? 'Reviewers can approve this campaign'
                  : 'Notify reviewers this campaign is ready for feedback'}
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={isInReview}
              onClick={handleMarkInReview}
              disabled={isMarkingInReview || campaign.status === 'approved'}
              className={[
                'relative flex-shrink-0 w-10 h-6 rounded-full transition-colors duration-200',
                'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                isInReview ? 'bg-brand-primary' : 'bg-neutral-300',
              ].join(' ')}
            >
              <span
                className={[
                  'absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-200',
                  isInReview ? 'translate-x-5' : 'translate-x-1',
                ].join(' ')}
              />
            </button>
          </div>
          {campaign.status === 'approved' && (
            <p className="text-caption text-success-600">
              ✓ This campaign has been approved.
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-1 border-t border-neutral-100">
          <Button type="button" variant="ghost" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </Modal>
  )
}
