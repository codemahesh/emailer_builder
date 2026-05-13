import { useCallback, useRef, useState } from 'react'
import { Modal } from '../ui/Modal'
import { replaceProductImage, type Product } from '../../lib/api'
import { showToast } from '../ui/Toast'

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

interface ImageEditPopoverProps {
  isOpen: boolean
  onClose: () => void
  campaignId: string
  productId: string
  onSuccess: (updated: Product) => void
}

type Tab = 'upload' | 'url'

export function ImageEditPopover({
  isOpen,
  onClose,
  campaignId,
  productId,
  onSuccess,
}: ImageEditPopoverProps) {
  const [activeTab, setActiveTab] = useState<Tab>('upload')
  const [imageUrl, setImageUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleClose = useCallback(() => {
    setImageUrl('')
    setActiveTab('upload')
    if (fileInputRef.current) fileInputRef.current.value = ''
    onClose()
  }, [onClose])

  const handleFileSubmit = useCallback(async () => {
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      showToast('Please select a file', 'warn')
      return
    }
    if (file.size > MAX_FILE_SIZE) {
      showToast('File must be under 10MB', 'error')
      return
    }
    if (!file.type.startsWith('image/')) {
      showToast('File must be an image', 'error')
      return
    }
    setIsSubmitting(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const updated = await replaceProductImage(campaignId, productId, formData)
      onSuccess(updated)
      handleClose()
    } catch {
      showToast('Failed to upload image', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }, [campaignId, productId, onSuccess, handleClose])

  const handleUrlSubmit = useCallback(async () => {
    if (!imageUrl.trim()) {
      showToast('Please enter an image URL', 'warn')
      return
    }
    setIsSubmitting(true)
    try {
      const updated = await replaceProductImage(campaignId, productId, { image_url: imageUrl.trim() })
      onSuccess(updated)
      handleClose()
    } catch {
      showToast('Failed to update image URL', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }, [campaignId, productId, imageUrl, onSuccess, handleClose])

  const handleSubmit = useCallback(() => {
    if (activeTab === 'upload') handleFileSubmit()
    else handleUrlSubmit()
  }, [activeTab, handleFileSubmit, handleUrlSubmit])

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Edit photo" width="sm">
      <div className="p-6 flex flex-col gap-4">
        {/* Tabs */}
        <div className="flex border-b border-neutral-200">
          {(['upload', 'url'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={[
                'px-4 py-2 text-body-strong -mb-px border-b-2 transition-colors',
                activeTab === tab
                  ? 'border-brand-primary text-brand-primary'
                  : 'border-transparent text-neutral-500 hover:text-neutral-800',
              ].join(' ')}
            >
              {tab === 'upload' ? 'Upload file' : 'Paste image URL'}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'upload' ? (
          <div className="flex flex-col gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="text-body text-neutral-800 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-body file:bg-neutral-100 file:text-neutral-800 hover:file:bg-neutral-200 cursor-pointer"
            />
            <p className="text-small text-neutral-400">Max file size: 10MB. Images only.</p>
          </div>
        ) : (
          <input
            type="url"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit() }}
            placeholder="https://…"
            className="w-full text-body text-neutral-800 px-3 py-2 rounded border border-neutral-200 outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
          />
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={handleClose}
            className="px-3 py-1.5 text-body text-neutral-600 rounded hover:bg-neutral-100 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-4 py-1.5 text-body-strong text-neutral-0 rounded bg-brand-primary hover:bg-brand-primary-hover transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
