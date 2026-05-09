import React, { useRef, useState } from 'react'
import { Modal } from './ui/Modal'
import { Button } from './ui/Button'
import { replaceProductImage, type Product } from '../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface QualityWarningCardProps {
  isOpen: boolean
  onClose: () => void
  product: Product
  campaignId: string
  onReplaced: (newImageUrl: string) => void
}

type Tab = 'upload' | 'url'

// ── Component ─────────────────────────────────────────────────────────────────

export function QualityWarningCard({
  isOpen,
  onClose,
  product,
  campaignId,
  onReplaced,
}: QualityWarningCardProps) {
  const [activeTab, setActiveTab] = useState<Tab>('upload')
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [urlValue, setUrlValue] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Reset state when modal opens/closes ────────────────────────────────────
  const handleClose = () => {
    setActiveTab('upload')
    setSelectedFile(null)
    setUrlValue('')
    setIsSubmitting(false)
    setErrorMessage('')
    setSuccessMessage('')
    setIsDragging(false)
    onClose()
  }

  // ── File selection helpers ─────────────────────────────────────────────────
  const handleFileSelect = (file: File) => {
    if (!file.type.startsWith('image/')) {
      setErrorMessage('Please select an image file (JPEG, PNG, GIF, WebP, etc.)')
      return
    }
    setErrorMessage('')
    setSelectedFile(file)
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFileSelect(file)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFileSelect(file)
  }

  // ── Submit ─────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    setErrorMessage('')
    setIsSubmitting(true)

    try {
      let updatedProduct: typeof product

      if (activeTab === 'upload') {
        if (!selectedFile) {
          setErrorMessage('Please select a file to upload.')
          setIsSubmitting(false)
          return
        }
        const formData = new FormData()
        formData.append('file', selectedFile)
        updatedProduct = await replaceProductImage(campaignId, product.id, formData)
      } else {
        const trimmed = urlValue.trim()
        if (!trimmed) {
          setErrorMessage('Please enter an image URL.')
          setIsSubmitting(false)
          return
        }
        const formData = new FormData()
        formData.append('image_url', trimmed)
        updatedProduct = await replaceProductImage(campaignId, product.id, formData)
      }

      setSuccessMessage('Image replaced')
      onReplaced(updatedProduct.scraped_image_url ?? '')

      setTimeout(() => {
        handleClose()
      }, 1500)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      const detail =
        e?.response?.data?.detail ?? 'Failed to replace image. Please try again.'
      setErrorMessage(detail)
    } finally {
      setIsSubmitting(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  const thumbnailSrc = product.scraped_image_url ?? '/static/coming-soon.svg'

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Image quality issue" width="md">
      <div className="flex flex-col gap-0">
        {/* Product summary row */}
        <div className="flex items-start gap-4 px-6 py-4 border-b border-neutral-100">
          {/* Thumbnail */}
          <div className="w-16 h-16 rounded-md bg-neutral-100 flex-shrink-0 overflow-hidden border border-neutral-200">
            <img
              src={thumbnailSrc}
              alt={product.scraped_name ?? product.sku}
              className="w-full h-full object-cover"
              onError={(e) => {
                ;(e.currentTarget as HTMLImageElement).src = '/static/coming-soon.svg'
              }}
            />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <p className="text-small-strong text-neutral-800 truncate">
              {product.scraped_name ?? product.sku}
            </p>
            <p className="text-small text-neutral-400 truncate">SKU: {product.sku}</p>
          </div>
        </div>

        {/* Verdict badge */}
        <div className="px-6 py-3 border-b border-neutral-100">
          <span className="inline-flex items-center gap-1.5 text-small px-3 py-1.5 rounded-full bg-warning-50 text-warning-700 border border-warning-200">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path
                d="M7 5.25v2.5M7 9.25v.25M1.5 11.5h11L7 2.5l-5.5 9z"
                stroke="currentColor"
                strokeWidth="1.25"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Scrape failed — image could not be loaded
          </span>
        </div>

        {/* Tab bar */}
        <div className="flex border-b border-neutral-100 px-6">
          {(['upload', 'url'] as Tab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => {
                setActiveTab(tab)
                setErrorMessage('')
                setSelectedFile(null)
                setUrlValue('')
              }}
              className={[
                'px-4 py-3 text-small-strong border-b-2 transition-colors',
                activeTab === tab
                  ? 'border-brand-primary text-brand-primary'
                  : 'border-transparent text-neutral-500 hover:text-neutral-700',
              ].join(' ')}
            >
              {tab === 'upload' ? 'Upload file' : 'Paste URL'}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="px-6 py-5 flex flex-col gap-4">
          {successMessage ? (
            <div className="flex items-center justify-center gap-2 py-4 text-success-600">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path
                  d="M7 10l2.5 2.5L14 7M10 19C5.029 19 1 14.971 1 10S5.029 1 10 1s9 4.029 9 9-4.029 9-9 9z"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="text-body-strong">{successMessage}</span>
            </div>
          ) : activeTab === 'upload' ? (
            /* Upload tab */
            <div className="flex flex-col gap-3">
              {/* Drop zone */}
              <div
                className={[
                  'flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer',
                  isDragging
                    ? 'border-brand-primary bg-brand-50'
                    : 'border-neutral-200 bg-neutral-50 hover:border-neutral-400',
                ].join(' ')}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    fileInputRef.current?.click()
                  }
                }}
                aria-label="Drop image here or click to browse"
              >
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 32 32"
                  fill="none"
                  className="text-neutral-400"
                  aria-hidden="true"
                >
                  <path
                    d="M10.667 21.333A5.333 5.333 0 0 1 10.667 10.667h.333A6.667 6.667 0 0 1 23.333 14v.333A4 4 0 0 1 22.667 22"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M19.333 21.333 16 18l-3.333 3.333M16 18v8"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>

                {selectedFile ? (
                  <div className="text-center">
                    <p className="text-small-strong text-neutral-700 truncate max-w-[240px]">
                      {selectedFile.name}
                    </p>
                    <p className="text-small text-neutral-400 mt-0.5">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                ) : (
                  <div className="text-center">
                    <p className="text-small-strong text-neutral-600">
                      Drop image here or click to browse
                    </p>
                    <p className="text-small text-neutral-400 mt-0.5">
                      JPEG, PNG, GIF, WebP — max 10 MB
                    </p>
                  </div>
                )}
              </div>

              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileInputChange}
                aria-hidden="true"
              />

              {selectedFile && (
                <Button
                  variant="primary"
                  fullWidth
                  isLoading={isSubmitting}
                  disabled={isSubmitting}
                  onClick={handleSubmit}
                >
                  {isSubmitting ? 'Uploading…' : 'Use this image'}
                </Button>
              )}
            </div>
          ) : (
            /* URL tab */
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="image-url-input"
                  className="text-small-strong text-neutral-700"
                >
                  Image URL
                </label>
                <input
                  id="image-url-input"
                  type="url"
                  value={urlValue}
                  onChange={(e) => setUrlValue(e.target.value)}
                  placeholder="https://example.com/product-image.jpg"
                  className="w-full rounded-md border border-neutral-200 px-3 py-2 text-body text-neutral-800 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && urlValue.trim()) handleSubmit()
                  }}
                />
              </div>

              <Button
                variant="primary"
                fullWidth
                isLoading={isSubmitting}
                disabled={isSubmitting || !urlValue.trim()}
                onClick={handleSubmit}
              >
                {isSubmitting ? 'Fetching…' : 'Use this image'}
              </Button>
            </div>
          )}

          {/* Error message */}
          {errorMessage && !successMessage && (
            <p className="text-small text-error-600 flex items-start gap-1.5">
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                className="flex-shrink-0 mt-0.5"
                aria-hidden="true"
              >
                <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.25" />
                <path
                  d="M7 4.5v3M7 9v.5"
                  stroke="currentColor"
                  strokeWidth="1.25"
                  strokeLinecap="round"
                />
              </svg>
              {errorMessage}
            </p>
          )}
        </div>

        {/* Footer note */}
        {!successMessage && (
          <div className="px-6 py-3 border-t border-neutral-100 bg-neutral-50 rounded-b-lg">
            <p className="text-small text-neutral-400">
              Replacement image is checked for validity before saving.
            </p>
          </div>
        )}
      </div>
    </Modal>
  )
}
