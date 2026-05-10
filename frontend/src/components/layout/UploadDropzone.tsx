import { useCallback, useRef, useState } from 'react'
import { uploadSheetFile, type UploadResponse } from '../../lib/api'

interface UploadDropzoneProps {
  campaignId: string
  onSuccess: (response: UploadResponse) => void
}

type DropzoneState = 'idle' | 'dragover' | 'uploading' | 'error' | 'success'

const UPLOAD_ERROR_COPY: Record<string, { title: string; body: string }> = {
  INVALID_TYPE: {
    title: 'Unsupported file type.',
    body: 'Please upload a .xlsx or .csv file.',
  },
  FILE_TOO_LARGE: {
    title: 'File is too large.',
    body: 'Files must be under 5 MB.',
  },
  TOO_MANY_ROWS: {
    title: 'Too many rows.',
    body: 'Files must contain 10,000 rows or fewer.',
  },
  PARSE_ERROR: {
    title: 'Could not read the file.',
    body: 'The file may be corrupted or in an unsupported format.',
  },
  EMPTY_SHEET: {
    title: 'Sheet is empty.',
    body: 'The file has no data rows.',
  },
  MISSING_COLUMNS: {
    title: '',
    body: 'Your file must include "sku" and "product_link". Use the template to get the headers right.',
  },
}

export function UploadDropzone({ campaignId, onSuccess }: UploadDropzoneProps) {
  const [state, setState] = useState<DropzoneState>('idle')
  const [error, setError] = useState<UploadResponse | null>(null)
  const [progress, setProgress] = useState<string | null>(null)

  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const handleFile = useCallback(
    async (file: File) => {
      setError(null)
      setState('uploading')
      setProgress('Uploading…')

      const abort = new AbortController()
      abortRef.current = abort

      try {
        const res = await uploadSheetFile(campaignId, file, abort.signal)
        if (res.ok) {
          setState('success')
          setProgress(null)
          onSuccess(res)
        } else {
          setState('error')
          setProgress(null)
          setError(res)
        }
      } catch (err: unknown) {
        if ((err as { name?: string }).name === 'CanceledError' || (err as { name?: string }).name === 'AbortError') {
          setState('idle')
          setProgress(null)
        } else {
          setState('error')
          setProgress(null)
          setError({ ok: false, error_code: 'PARSE_ERROR', headers_found: [], missing_columns: [], row_count: 0, version_id: null, imported_count: 0 })
        }
      } finally {
        abortRef.current = null
      }
    },
    [campaignId, onSuccess],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setState('idle')
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const handleCancel = () => {
    abortRef.current?.abort()
  }

  const errorCode = error?.error_code ?? ''
  const copy = UPLOAD_ERROR_COPY[errorCode] ?? { title: 'Upload failed.', body: '' }
  const title =
    errorCode === 'MISSING_COLUMNS'
      ? error!.missing_columns.length === 1
        ? `Missing column: ${error!.missing_columns[0]}`
        : `Missing columns: ${error!.missing_columns.join(', ')}`
      : copy.title

  return (
    <div className="flex flex-col gap-3">
      {/* Dropzone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload spreadsheet file"
        onDragOver={(e) => { e.preventDefault(); if (state !== 'uploading') setState('dragover') }}
        onDragLeave={() => { if (state !== 'uploading') setState('idle') }}
        onDrop={handleDrop}
        onClick={() => { if (state !== 'uploading') inputRef.current?.click() }}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
        className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed py-8 px-4 cursor-pointer transition-colors outline-none focus:ring-2 focus:ring-brand-primary ${
          state === 'dragover'
            ? 'border-brand-primary bg-brand-50'
            : state === 'uploading'
            ? 'border-neutral-200 bg-neutral-50 cursor-not-allowed'
            : state === 'success'
            ? 'border-success-400 bg-success-50'
            : state === 'error'
            ? 'border-error-300 bg-error-50'
            : 'border-neutral-300 hover:border-brand-primary bg-white'
        }`}
      >
        {state === 'uploading' ? (
          <>
            <svg className="animate-spin w-8 h-8 text-brand-primary" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeDasharray="60" strokeDashoffset="40" />
            </svg>
            <p className="text-small text-neutral-600">{progress}</p>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); handleCancel() }}
              className="text-small text-neutral-400 hover:text-neutral-600 underline"
            >
              Cancel
            </button>
          </>
        ) : state === 'success' ? (
          <>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <circle cx="16" cy="16" r="13" stroke="#16a34a" strokeWidth="2" />
              <path d="M10 16l4 4 8-8" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="text-small text-success-700 font-semibold">Uploaded successfully</p>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setState('idle'); setError(null) }}
              className="text-small text-success-600 underline hover:no-underline"
            >
              Replace file
            </button>
          </>
        ) : (
          <>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true" className={state === 'dragover' ? 'text-brand-primary' : 'text-neutral-400'}>
              <path d="M16 4v16M10 10l6-6 6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M6 24h20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <div className="text-center">
              <p className="text-small-strong text-neutral-700">
                Drop your file here or <span className="text-brand-primary underline">browse</span>
              </p>
              <p className="text-small text-neutral-400 mt-0.5">.xlsx or .csv · max 5 MB · 10,000 rows</p>
            </div>
            <div className="flex items-center gap-3 text-small text-neutral-400">
              <span>Need a template?</span>
              <a
                href="/static/sheet-template.xlsx"
                download="sheet-template.xlsx"
                className="flex items-center gap-1 text-neutral-500 hover:text-brand-primary transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                  <path d="M6.5 1v7.5M3.5 6l3 3 3-3M1 10.5h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Excel
              </a>
              <a
                href="/static/sheet-template.csv"
                download="sheet-template.csv"
                className="flex items-center gap-1 text-neutral-500 hover:text-brand-primary transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                  <path d="M6.5 1v7.5M3.5 6l3 3 3-3M1 10.5h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                CSV
              </a>
            </div>
          </>
        )}
      </div>

      {/* Error banner */}
      {state === 'error' && error && (
        <div
          role="alert"
          className="rounded-lg border border-error-200 bg-error-50 p-3 flex flex-col gap-2 text-small text-error-800"
        >
          <div className="flex items-start gap-2">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0 mt-0.5 text-error-600" aria-hidden="true">
              <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5" />
              <path d="M8 5v3.5M8 10.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <div>
              {title && <p className="font-semibold">{title}</p>}
              {copy.body && <p className={title ? 'mt-0.5' : ''}>{copy.body}</p>}
            </div>
          </div>
          {errorCode === 'MISSING_COLUMNS' && (
            <div className="pl-6">
              <a
                href="/static/sheet-template.xlsx"
                download
                className="text-small-strong text-error-700 underline hover:no-underline"
              >
                ⤓ Download template
              </a>
            </div>
          )}
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFile(file)
          e.target.value = ''
        }}
        aria-hidden="true"
      />
    </div>
  )
}
