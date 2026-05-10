import type { ImportPreflightResponse } from '../../lib/api'

interface UpdateSummaryProps {
  diff: ImportPreflightResponse
  onApply: () => void
  onCancel: () => void
  isApplying: boolean
}

export function UpdateSummary({ diff, onApply, onCancel, isApplying }: UpdateSummaryProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 flex flex-col gap-3">
      <p className="text-small-strong text-neutral-700">Changes detected:</p>

      <ul className="flex flex-col gap-1.5 text-small">
        {diff.added > 0 && (
          <li className="flex items-center gap-2 text-success-700">
            <span className="w-4 text-center font-semibold">+</span>
            Add {diff.added} product{diff.added !== 1 ? 's' : ''}
          </li>
        )}
        {diff.removed > 0 && (
          <li className="flex items-center gap-2 text-error-700">
            <span className="w-4 text-center font-semibold">−</span>
            Remove {diff.removed} (kept in history)
          </li>
        )}
        {diff.updated > 0 && (
          <li className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-neutral-700">
              <span className="w-4 text-center font-semibold">≠</span>
              Update {diff.updated} product{diff.updated !== 1 ? 's' : ''}
            </div>
            {diff.rescrape_count > 0 && (
              <div className="pl-6 text-neutral-500">
                ↳ {diff.rescrape_count} will be re-scraped (link changed)
              </div>
            )}
          </li>
        )}
        {diff.unchanged > 0 && (
          <li className="flex items-center gap-2 text-neutral-400">
            <span className="w-4 text-center">·</span>
            {diff.unchanged} unchanged
          </li>
        )}
      </ul>

      <div className="flex items-center gap-2 justify-end pt-1">
        <button
          type="button"
          onClick={onCancel}
          disabled={isApplying}
          className="px-3 py-1.5 text-small rounded border border-neutral-200 text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onApply}
          disabled={isApplying}
          className="px-3 py-1.5 text-small rounded bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50 transition-colors"
        >
          {isApplying ? 'Applying…' : 'Apply'}
        </button>
      </div>
    </div>
  )
}
