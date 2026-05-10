import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { Skeleton } from '../components/ui/Skeleton'
import { Button } from '../components/ui/Button'
import { showToast } from '../components/ui/Toast'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ReviewData {
  html: string
  campaign_name: string
  last_updated: string
}

interface ReviewComment {
  id: string
  author_name: string
  body: string
  section_id: string | null
  created_at: string
}

type Viewport = 'desktop' | 'mobile'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

// ── Skeleton loader ───────────────────────────────────────────────────────────

function ReviewSkeleton() {
  return (
    <div className="flex flex-col flex-1 items-center justify-start pt-10 px-4 gap-4" aria-busy="true">
      <Skeleton className="w-[600px] max-w-full h-8" />
      <Skeleton className="w-[600px] max-w-full h-[400px]" rounded="md" />
      <Skeleton className="w-[600px] max-w-full h-[200px]" rounded="md" />
    </div>
  )
}

// ── Comment Drawer ────────────────────────────────────────────────────────────

interface CommentDrawerProps {
  token: string
  isOpen: boolean
  onClose: () => void
  onSubmitted: () => void
}

function CommentDrawer({ token, isOpen, onClose, onSubmitted }: CommentDrawerProps) {
  const [authorName, setAuthorName] = useState('')
  const [body, setBody] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!authorName.trim() || !body.trim()) return
    setIsSubmitting(true)
    try {
      await api.post(`/review/${token}/comments`, {
        author_name: authorName.trim(),
        body: body.trim(),
        section_id: null,
      })
      showToast('Comment posted', 'success')
      setAuthorName('')
      setBody('')
      onSubmitted()
      onClose()
    } catch {
      showToast('Failed to post comment', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-40 flex items-end sm:items-center justify-center bg-neutral-900/60 backdrop-blur-[2px]"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      role="dialog"
      aria-modal="true"
      aria-label="Add a comment"
    >
      <div className="w-full max-w-lg bg-neutral-0 rounded-t-2xl sm:rounded-lg shadow-elev-modal p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-heading-3 text-neutral-900">Add a comment</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close comment drawer"
            className="w-8 h-8 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="author-name" className="text-small text-neutral-600">Your name</label>
            <input
              id="author-name"
              type="text"
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
              placeholder="e.g. Jane Smith"
              required
              className="h-9 px-3 rounded-md border border-neutral-200 bg-neutral-0 text-body text-neutral-800 placeholder:text-neutral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="comment-body" className="text-small text-neutral-600">Comment</label>
            <textarea
              id="comment-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Write your feedback..."
              required
              rows={4}
              className="px-3 py-2 rounded-md border border-neutral-200 bg-neutral-0 text-body text-neutral-800 placeholder:text-neutral-400 resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
            />
          </div>
          <div className="flex justify-end gap-3 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              disabled={!authorName.trim() || !body.trim() || isSubmitting}
            >
              Post comment
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Comments Sheet ─────────────────────────────────────────────────────────────

interface CommentsSheetProps {
  token: string
  isOpen: boolean
  onClose: () => void
  comments: ReviewComment[]
}

function CommentsSheet({ isOpen, onClose, comments }: CommentsSheetProps) {
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center bg-neutral-900/60 backdrop-blur-[2px]"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      role="dialog"
      aria-modal="true"
      aria-label="Comments"
    >
      <div className="w-full max-w-2xl bg-neutral-0 rounded-t-2xl shadow-elev-modal flex flex-col max-h-[70vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 flex-shrink-0">
          <h2 className="text-heading-3 text-neutral-900">Comments ({comments.length})</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close comments"
            className="w-8 h-8 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
          {comments.length === 0 ? (
            <p className="text-body text-neutral-400 text-center py-8">No comments yet.</p>
          ) : (
            comments.map((comment) => (
              <div key={comment.id} className="flex flex-col gap-1 p-4 rounded-lg border border-neutral-200 bg-neutral-50">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-small-strong text-neutral-800">{comment.author_name}</span>
                  <span className="text-caption text-neutral-400">{formatDateTime(comment.created_at)}</span>
                </div>
                <p className="text-body text-neutral-600">{comment.body}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// ── Approve Confirmation Modal ────────────────────────────────────────────────

interface ApproveModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  viewportConfirmed: 'desktop' | 'mobile' | 'both'
  isSubmitting: boolean
}

function ApproveModal({ isOpen, onClose, onConfirm, viewportConfirmed, isSubmitting }: ApproveModalProps) {
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/60 backdrop-blur-[2px]"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="approve-modal-title"
    >
      <div className="w-full max-w-sm bg-neutral-0 rounded-lg shadow-elev-modal flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
          <h2 id="approve-modal-title" className="text-heading-3 text-neutral-900">Confirm approval</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="w-8 h-8 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <div className="px-6 py-5 flex flex-col gap-3">
          <p className="text-body text-neutral-600">This logs your approval — continue?</p>
          {viewportConfirmed === 'mobile' && (
            <p className="text-small text-warn-600 bg-warn-50 border border-warn-200 rounded-md px-3 py-2">
              You reviewed Mobile only — also confirm Desktop?
            </p>
          )}
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-100">
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            isLoading={isSubmitting}
            onClick={onConfirm}
          >
            Approve
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function ReviewPage() {
  const { token } = useParams<{ token: string }>()

  const [reviewData, setReviewData] = useState<ReviewData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const [viewport, setViewport] = useState<Viewport>('desktop')
  const [viewportEverSwitched, setViewportEverSwitched] = useState(false)
  const [viewportConfirmed, setViewportConfirmed] = useState<'desktop' | 'mobile' | 'both'>('desktop')

  const [comments, setComments] = useState<ReviewComment[]>([])
  const [commentCount, setCommentCount] = useState(0)
  const [showComments, setShowComments] = useState(false)
  const [showCommentDrawer, setShowCommentDrawer] = useState(false)

  const [showApproveModal, setShowApproveModal] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [approvedAt, setApprovedAt] = useState<string | null>(null)

  const iframeRef = useRef<HTMLIFrameElement>(null)

  // ── Load review data ────────────────────────────────────────────────────────

  const loadReview = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const res = await api.get<ReviewData>(`/review/${token}`)
      setReviewData(res.data)
    } catch (err: unknown) {
      const e = err as { response?: { status?: number } }
      if (e?.response?.status === 404) {
        setNotFound(true)
      } else {
        showToast('Failed to load preview', 'error')
        setNotFound(true)
      }
    } finally {
      setIsLoading(false)
    }
  }, [token])

  const loadComments = useCallback(async () => {
    if (!token) return
    try {
      const res = await api.get<ReviewComment[]>(`/review/${token}/comments`)
      setComments(res.data)
      setCommentCount(res.data.length)
    } catch {
      // silently fail — comment count non-critical
    }
  }, [token])

  useEffect(() => {
    loadReview()
    loadComments()
  }, [loadReview, loadComments])

  // ── Write HTML into iframe ──────────────────────────────────────────────────

  useEffect(() => {
    if (!reviewData?.html || !iframeRef.current) return
    const doc = iframeRef.current.contentDocument
    if (doc) {
      doc.open()
      doc.write(reviewData.html)
      doc.close()
    }
  }, [reviewData?.html, viewport])

  // ── Viewport toggle ─────────────────────────────────────────────────────────

  const handleViewportChange = (v: Viewport) => {
    if (v === viewport) return
    setViewport(v)
    if (!viewportEverSwitched) setViewportEverSwitched(true)
    // Track which viewports have been confirmed
    setViewportConfirmed((prev) => {
      if (prev === 'both') return 'both'
      if (v === 'desktop' && prev === 'mobile') return 'both'
      if (v === 'mobile' && prev === 'desktop') return 'both'
      return v
    })
  }

  // ── Approve ─────────────────────────────────────────────────────────────────

  const handleApproveClick = () => {
    setShowApproveModal(true)
  }

  const handleApproveConfirm = async () => {
    if (!token) return
    setIsApproving(true)
    try {
      await api.post(`/review/${token}/approve`, {
        reviewer_name: 'Reviewer',
        viewport_confirmed: viewportConfirmed,
      })
      setApprovedAt(new Date().toISOString())
      showToast('Approval logged successfully', 'success')
      setShowApproveModal(false)
    } catch {
      showToast('Failed to submit approval', 'error')
    } finally {
      setIsApproving(false)
    }
  }

  // ── 404 state ───────────────────────────────────────────────────────────────

  if (notFound) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-50 p-4">
        <div className="max-w-sm w-full bg-neutral-0 rounded-lg border border-neutral-200 shadow-elev-overlay p-8 text-center flex flex-col gap-4">
          <div className="w-12 h-12 rounded-full bg-neutral-100 flex items-center justify-center mx-auto">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="9" stroke="#9CA3AF" strokeWidth="1.5" />
              <path d="M12 8v5M12 15.5v.5" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="text-heading-2 text-neutral-800">This preview link is no longer valid</h1>
          <p className="text-body text-neutral-400">
            The link may have expired or been revoked. Please contact the campaign owner.
          </p>
          <a
            href="mailto:support@emailbuilder.com"
            className="text-brand-primary text-body hover:underline focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1 rounded"
          >
            Contact support
          </a>
        </div>
      </div>
    )
  }

  const iframeWidth = viewport === 'desktop' ? 600 : 375

  return (
    <div className="min-h-screen flex flex-col bg-neutral-100">
      {/* Skip link */}
      <a
        href="#comments"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-neutral-0 focus:px-3 focus:py-1 focus:rounded focus:text-body focus:text-brand-primary focus:shadow-elev-overlay"
      >
        Jump to comments
      </a>

      {/* Sticky top bar */}
      <header className="sticky top-0 z-20 h-12 bg-neutral-900 flex items-center justify-between px-4 gap-4 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-small-strong text-neutral-0 truncate">
            {isLoading ? (
              <Skeleton className="w-40 h-4" />
            ) : (
              reviewData?.campaign_name ?? ''
            )}
          </span>
          {!isLoading && reviewData?.last_updated && (
            <span className="text-caption text-neutral-400 flex-shrink-0">
              · Last updated {formatTime(reviewData.last_updated)}
            </span>
          )}
        </div>

        {/* Viewport segmented control */}
        <div
          className="flex items-center gap-0.5 bg-neutral-800 rounded-md p-0.5 flex-shrink-0"
          role="group"
          aria-label="Viewport toggle"
        >
          {(['desktop', 'mobile'] as Viewport[]).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => handleViewportChange(v)}
              aria-pressed={viewport === v}
              className={[
                'px-3 py-1 rounded text-caption transition-colors',
                viewport === v
                  ? 'bg-neutral-0 text-neutral-900 font-semibold'
                  : 'text-neutral-400 hover:text-neutral-200',
              ].join(' ')}
            >
              {v === 'desktop' ? 'D' : 'M'}
            </button>
          ))}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col items-center py-6 px-4 pb-24">
        {isLoading ? (
          <ReviewSkeleton />
        ) : (
          <div
            className="relative bg-neutral-0 rounded-lg shadow-elev-overlay overflow-hidden transition-all duration-300"
            style={{ width: iframeWidth, maxWidth: '100%' }}
          >
            <iframe
              ref={iframeRef}
              title="Email preview"
              sandbox="allow-same-origin"
              style={{ width: iframeWidth, maxWidth: '100%', minHeight: 600, border: 'none', display: 'block' }}
              aria-label="Email preview"
            />
          </div>
        )}
      </main>

      {/* Sticky bottom bar */}
      <footer
        id="comments"
        className="fixed bottom-0 left-0 right-0 z-20 h-16 bg-neutral-0 border-t border-neutral-200 flex items-center justify-between px-4 sm:px-6 shadow-elev-overlay"
      >
        <button
          type="button"
          onClick={() => setShowComments(true)}
          className="text-body text-neutral-600 hover:text-neutral-900 transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1 rounded"
          aria-label={`View ${commentCount} comment${commentCount !== 1 ? 's' : ''}`}
        >
          Comments ({commentCount})
        </button>

        {approvedAt ? (
          <div className="flex items-center gap-2 px-4 py-2 rounded-md bg-success-50 border border-success-200">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M2.5 7L5.5 10L11.5 4" stroke="#16a34a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="text-small-strong text-success-600">Approved at {formatTime(approvedAt)}</span>
          </div>
        ) : (
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={handleApproveClick}
            disabled={isLoading}
          >
            Approve
          </Button>
        )}
      </footer>

      {/* FAB comment button (mobile) / text link (desktop) */}
      {!isLoading && (
        <>
          {/* Mobile FAB */}
          <button
            type="button"
            onClick={() => setShowCommentDrawer(true)}
            aria-label="Add a comment"
            className="fixed bottom-20 right-4 z-30 sm:hidden flex items-center gap-2 px-4 py-3 rounded-full bg-info-600 text-neutral-0 shadow-elev-overlay text-small-strong hover:opacity-90 transition-opacity focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          >
            <span aria-hidden="true">&#128172;</span> Comment
          </button>
          {/* Desktop text link */}
          <button
            type="button"
            onClick={() => setShowCommentDrawer(true)}
            className="hidden sm:flex fixed bottom-20 right-6 z-30 items-center gap-1.5 text-body text-brand-primary hover:text-brand-primary-hover hover:underline transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1 rounded"
          >
            <span aria-hidden="true">&#128172;</span> Comment
          </button>
        </>
      )}

      {/* Modals & sheets */}
      <CommentDrawer
        token={token ?? ''}
        isOpen={showCommentDrawer}
        onClose={() => setShowCommentDrawer(false)}
        onSubmitted={() => loadComments()}
      />

      <CommentsSheet
        token={token ?? ''}
        isOpen={showComments}
        onClose={() => setShowComments(false)}
        comments={comments}
      />

      <ApproveModal
        isOpen={showApproveModal}
        onClose={() => setShowApproveModal(false)}
        onConfirm={handleApproveConfirm}
        viewportConfirmed={viewportConfirmed}
        isSubmitting={isApproving}
      />
    </div>
  )
}
