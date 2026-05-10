import { useCallback, useEffect, useRef, useState, KeyboardEvent } from 'react'
import { getSheetPreview, verifySheet, type SheetPreviewResponse } from '../../lib/api'

interface PreviewTableProps {
  campaignId: string
  sheetUrl?: string
  isUploadSource?: boolean
  onUpdateListFocus?: () => void
}

const PAGE_SIZE = 50

type RefreshState = 'idle' | 'checking' | 'no_changes' | 'has_changes'

export function PreviewTable({ campaignId, sheetUrl, isUploadSource, onUpdateListFocus }: PreviewTableProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<SheetPreviewResponse | null>(null)
  const [offset, setOffset] = useState(0)
  const [focusedRow, setFocusedRow] = useState<number>(-1)
  const [refreshState, setRefreshState] = useState<RefreshState>('idle')

  const tbodyRef = useRef<HTMLTableSectionElement>(null)
  const fetchedRef = useRef(false)

  const fetchPage = useCallback(
    async (nextOffset: number) => {
      setLoading(true)
      try {
        const result = await getSheetPreview(campaignId, {
          limit: PAGE_SIZE,
          offset: nextOffset,
        })
        setData(result)
        setOffset(nextOffset)
        setFocusedRow(-1)
      } catch {
        // silently ignore — preview is best-effort
      } finally {
        setLoading(false)
      }
    },
    [campaignId],
  )

  // Fetch when first opened
  useEffect(() => {
    if (open && !fetchedRef.current) {
      fetchedRef.current = true
      fetchPage(0)
    }
  }, [open, fetchPage])

  // Refresh probe: call /sheet/verify and compare row_count to snapshot
  const handleRefresh = useCallback(async () => {
    if (!sheetUrl || !data || isUploadSource) return
    setRefreshState('checking')
    try {
      const result = await verifySheet(campaignId, sheetUrl)
      if (result.ok) {
        const hasChanges = result.row_count !== data.row_count
        setRefreshState(hasChanges ? 'has_changes' : 'no_changes')
      } else {
        setRefreshState('idle')
      }
    } catch {
      setRefreshState('idle')
    }
  }, [campaignId, sheetUrl, data, isUploadSource])

  // ── Keyboard navigation ──────────────────────────────────────────────────
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTableSectionElement>) => {
      if (!data || data.rows.length === 0) return
      const last = data.rows.length - 1
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setFocusedRow((r) => Math.min(r + 1, last))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setFocusedRow((r) => Math.max(r - 1, 0))
      } else if (e.key === 'Home') {
        e.preventDefault()
        setFocusedRow(0)
      } else if (e.key === 'End') {
        e.preventDefault()
        setFocusedRow(last)
      }
    },
    [data],
  )

  // Focus the highlighted row element whenever focusedRow changes
  useEffect(() => {
    if (focusedRow >= 0 && tbodyRef.current) {
      const rows = tbodyRef.current.querySelectorAll('tr')
      rows[focusedRow]?.focus()
    }
  }, [focusedRow])

  const rowCount = data?.row_count ?? 0

  return (
    <div className="border border-neutral-200 rounded-lg overflow-hidden">
      {/* Disclosure header */}
      <button
        type="button"
        aria-expanded={open}
        aria-controls="preview-table-region"
        onClick={() => { setOpen((o) => !o); setRefreshState('idle') }}
        className="w-full flex items-center justify-between px-4 py-3 bg-neutral-50 hover:bg-neutral-100 transition-colors text-left"
      >
        <span className="flex items-center gap-2 text-small-strong text-neutral-700">
          <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
            aria-hidden="true"
            className={`transition-transform ${open ? 'rotate-90' : ''}`}
          >
            <path d="M3 2l4 3-4 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {open ? '▾' : '▸'} Preview {rowCount > 0 ? `${rowCount} products` : 'products'}
        </span>
        {loading && (
          <span className="text-small text-neutral-400 animate-pulse">Loading…</span>
        )}
      </button>

      {/* Table region */}
      <div
        id="preview-table-region"
        hidden={!open}
        className="overflow-auto max-h-96"
      >
        {data && data.version > 0 ? (
          <>
            {/* Snapshot caption + refresh icon */}
            <div className="flex items-center gap-2 px-4 py-2 bg-white border-b border-neutral-100 text-small text-neutral-500">
              <span>
                {refreshState === 'no_changes'
                  ? 'No changes since last import.'
                  : `Snapshot from v${data.version} — refresh to check live.`}
              </span>
              <button
                type="button"
                disabled={refreshState === 'checking' || isUploadSource || !sheetUrl}
                onClick={handleRefresh}
                title={isUploadSource ? 'No live source for upload connections' : 'Check the source for updates'}
                aria-label="Check the source for updates"
                className={`flex-shrink-0 transition-colors ${
                  refreshState === 'checking'
                    ? 'text-neutral-400 animate-spin cursor-wait'
                    : isUploadSource || !sheetUrl
                    ? 'text-neutral-200 cursor-not-allowed'
                    : 'text-neutral-400 hover:text-brand-primary cursor-pointer'
                }`}
              >
                <svg width="13" height="13" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M10 6A4 4 0 112 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M10 3v3H7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            {/* "Updates available" inline banner */}
            {refreshState === 'has_changes' && (
              <div className="px-4 py-2 bg-info-50 border-b border-info-200 flex items-center gap-2 text-small text-info-700">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="flex-shrink-0" aria-hidden="true">
                  <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M7 6v4M7 4.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span>Updates available —{' '}</span>
                <button
                  type="button"
                  onClick={() => { setRefreshState('idle'); onUpdateListFocus?.() }}
                  className="font-semibold underline hover:no-underline"
                >
                  Update List
                </button>
              </div>
            )}

            {data.rows.length === 0 ? (
              <p className="px-4 py-6 text-small text-neutral-400 text-center">No rows to preview.</p>
            ) : (
              <table className="w-full text-small border-collapse" role="grid">
                <thead className="bg-neutral-50 sticky top-0 z-10">
                  <tr>
                    {data.headers.map((h) => (
                      <th
                        key={h}
                        scope="col"
                        className="px-3 py-2 text-left font-semibold text-neutral-600 border-b border-neutral-200 whitespace-nowrap"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody
                  ref={tbodyRef}
                  onKeyDown={handleKeyDown}
                  className="divide-y divide-neutral-100"
                >
                  {data.rows.map((row, i) => (
                    <tr
                      key={i}
                      tabIndex={0}
                      aria-rowindex={offset + i + 2}
                      className={`cursor-pointer outline-none focus:bg-brand-50 hover:bg-neutral-50 ${
                        focusedRow === i ? 'bg-brand-50' : ''
                      }`}
                      onFocus={() => setFocusedRow(i)}
                    >
                      {data.headers.map((h) => (
                        <td
                          key={h}
                          className="px-3 py-2 text-neutral-700 whitespace-nowrap max-w-[200px] truncate"
                          title={row[h] ?? ''}
                        >
                          {row[h] ?? ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {/* Pagination */}
            {(offset > 0 || data.has_more) && (
              <div className="flex items-center justify-between px-4 py-2 border-t border-neutral-100 bg-white">
                <button
                  type="button"
                  disabled={offset === 0 || loading}
                  onClick={() => fetchPage(Math.max(0, offset - PAGE_SIZE))}
                  className="text-small text-neutral-500 disabled:text-neutral-300 hover:text-brand-primary disabled:cursor-not-allowed"
                >
                  ← Previous
                </button>
                <span className="text-small text-neutral-400">
                  Rows {offset + 1}–{offset + data.rows.length} of {data.row_count}
                </span>
                <button
                  type="button"
                  disabled={!data.has_more || loading}
                  onClick={() => fetchPage(offset + PAGE_SIZE)}
                  className="text-small text-neutral-500 disabled:text-neutral-300 hover:text-brand-primary disabled:cursor-not-allowed"
                >
                  Next →
                </button>
              </div>
            )}
          </>
        ) : !loading ? (
          <p className="px-4 py-6 text-small text-neutral-400 text-center">
            No snapshot available — run a Full Sync first.
          </p>
        ) : null}
      </div>
    </div>
  )
}
