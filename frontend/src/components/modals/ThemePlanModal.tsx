import { useCallback, useEffect, useRef, useState } from 'react'
import { previewThemePlan, applyThemePlan, type ThemePlan } from '../../lib/api'
import { showToast } from '../ui/Toast'

interface ThemePlanModalProps {
  campaignId: string
  isOpen: boolean
  onDone: () => void
}

type Phase = 'generating' | 'ready' | 'applying'

function ColorSwatch({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="flex-shrink-0 w-5 h-5 rounded-full border border-neutral-200 shadow-sm"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      <span className="text-small text-neutral-500">{label}</span>
      <span className="text-small text-neutral-400 font-mono ml-auto">{color}</span>
    </div>
  )
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-brand-primary"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

export function ThemePlanModal({ campaignId, isOpen, onDone }: ThemePlanModalProps) {
  const [phase, setPhase] = useState<Phase>('generating')
  const [plan, setPlan] = useState<ThemePlan | null>(null)
  const [feedback, setFeedback] = useState('')
  const feedbackRef = useRef<HTMLTextAreaElement>(null)

  const fetchPlan = useCallback(
    async (userFeedback = '') => {
      setPhase('generating')
      try {
        const result = await previewThemePlan(campaignId, userFeedback)
        setPlan(result)
        setPhase('ready')
      } catch {
        showToast('Could not generate theme — using defaults', 'error')
        onDone()
      }
    },
    [campaignId, onDone],
  )

  useEffect(() => {
    if (isOpen) {
      setFeedback('')
      setPlan(null)
      fetchPlan()
    }
  }, [isOpen, fetchPlan])

  const handleApply = useCallback(async () => {
    setPhase('applying')
    try {
      await applyThemePlan(campaignId, feedback.trim())
      onDone()
    } catch {
      showToast('Failed to apply theme — continuing without it', 'error')
      onDone()
    }
  }, [campaignId, feedback, onDone])

  const handleRefine = useCallback(() => {
    if (feedback.trim()) {
      fetchPlan(feedback.trim())
    }
  }, [feedback, fetchPlan])

  if (!isOpen) return null

  const isLoading = phase === 'generating' || phase === 'applying'
  const loadingMessage =
    phase === 'generating' ? 'Analyzing your products…' : 'Applying your theme…'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="theme-plan-title"
    >
      {/* Scrim — no close on backdrop since this is a post-approval gate */}
      <div className="absolute inset-0 bg-black/40" aria-hidden="true" />

      {/* Panel */}
      <div className="relative w-full max-w-[520px] bg-neutral-0 rounded-lg shadow-elev-modal flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center gap-2 px-6 pt-6 pb-4 border-b border-neutral-200">
          <span className="text-brand-primary text-lg" aria-hidden="true">✦</span>
          <h2 id="theme-plan-title" className="text-heading-2 text-neutral-800">
            Your Email Theme
          </h2>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-5">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center gap-3 py-10">
              <Spinner />
              <p className="text-body text-neutral-500">{loadingMessage}</p>
            </div>
          ) : plan ? (
            <>
              {/* Theme name + template badge */}
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-heading-3 text-neutral-900">{plan.theme_name}</h3>
                <span className="flex-shrink-0 px-2 py-0.5 rounded text-small text-brand-primary bg-brand-primary/10 border border-brand-primary/20">
                  {plan.template_id.replace('_', ' ')}
                </span>
              </div>

              {/* Color palette */}
              <div className="flex flex-col gap-2">
                <p className="text-small-strong text-neutral-600">Colour palette</p>
                <div className="flex flex-col gap-1.5 p-3 bg-neutral-50 rounded-md border border-neutral-100">
                  <ColorSwatch color={plan.background_color} label="Background" />
                  <ColorSwatch color={plan.section_color} label="Section" />
                  <ColorSwatch color={plan.accent_color} label="Accent" />
                  <ColorSwatch color={plan.button_color} label="Button" />
                </div>
              </div>

              {/* Typography */}
              <div className="flex flex-col gap-1">
                <p className="text-small-strong text-neutral-600">Typography</p>
                <p className="text-small text-neutral-700">
                  <span className="font-medium">Heading:</span>{' '}
                  {plan.heading_font.split(',')[0].trim()}
                  {' · '}
                  <span className="font-medium">Body:</span>{' '}
                  {plan.body_font.split(',')[0].trim()}
                </p>
              </div>

              {/* Rationale */}
              <div className="flex flex-col gap-1.5">
                <p className="text-small-strong text-neutral-600">Why this theme?</p>
                <p className="text-body text-neutral-700 leading-relaxed">{plan.rationale}</p>
              </div>

              {/* Feedback textarea */}
              <div className="flex flex-col gap-1.5">
                <label htmlFor="theme-feedback" className="text-small-strong text-neutral-600">
                  Refine the theme (optional)
                </label>
                <textarea
                  ref={feedbackRef}
                  id="theme-feedback"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  rows={2}
                  placeholder='e.g. "Make it warmer" or "Use bolder, more energetic colors"'
                  className={[
                    'w-full px-3 py-2 rounded-md border border-neutral-200 text-body text-neutral-800 resize-none',
                    'bg-neutral-0 placeholder:text-neutral-400',
                    'focus:outline-none focus:border-brand-primary focus-visible:ring-2 focus-visible:ring-brand-primary',
                    'transition-colors duration-[160ms]',
                  ].join(' ')}
                />
                {feedback.trim() && (
                  <button
                    type="button"
                    onClick={handleRefine}
                    className="self-start text-small text-brand-primary hover:underline"
                  >
                    Regenerate with this feedback
                  </button>
                )}
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        {!isLoading && (
          <div className="flex items-center justify-between gap-3 px-6 pb-6 pt-4 border-t border-neutral-100">
            <button
              type="button"
              onClick={onDone}
              className="text-body text-neutral-500 hover:text-neutral-700 transition-colors"
            >
              Skip for now
            </button>
            <button
              type="button"
              onClick={handleApply}
              className="px-5 py-2 rounded-md bg-brand-primary text-neutral-0 text-body-strong hover:bg-brand-primary-hover transition-colors"
            >
              Apply &amp; Continue
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
