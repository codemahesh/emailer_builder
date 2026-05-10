interface RescrapeProgressCardProps {
  done: number
  total: number
  lastSku?: string
}

export function RescrapeProgressCard({ done, total, lastSku }: RescrapeProgressCardProps) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0
  const label = total > 0
    ? `Re-scraping ${done} of ${total} changed products…`
    : 'Preparing re-scrape…'

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={label}
      className="flex flex-col gap-3 rounded-lg border border-brand-primary/20 bg-brand-50 p-4"
    >
      <p className="text-small-strong text-neutral-800">{label}</p>

      <div
        className="w-full h-2 rounded-full bg-brand-primary/20 overflow-hidden"
        role="progressbar"
        aria-valuenow={done}
        aria-valuemin={0}
        aria-valuemax={total || 1}
      >
        <div
          className="h-full bg-brand-primary transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>

      {lastSku && (
        <p className="text-small font-mono text-neutral-500">
          Last: {lastSku}{' '}
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            className="inline-block text-success-600"
            aria-hidden="true"
          >
            <path
              d="M2 6l3 3 5-5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </p>
      )}

      <p className="text-small text-neutral-400">
        You can leave this panel — sync will continue.
      </p>
    </div>
  )
}
