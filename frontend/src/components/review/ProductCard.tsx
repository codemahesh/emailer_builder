import { useCallback, useState } from 'react'
import { patchProduct, type Product, type ProductPatchBody } from '../../lib/api'
import { showToast } from '../ui/Toast'
import { InlineTextField } from './InlineTextField'
import { ImageEditPopover } from './ImageEditPopover'

const COMING_SOON_URL = '/static/coming-soon.svg'

interface ProductCardProps {
  product: Product
  campaignId: string
  onProductUpdate?: (updated: Product) => void
}

export function ProductCard({ product: initialProduct, campaignId, onProductUpdate }: ProductCardProps) {
  const [product, setProduct] = useState(initialProduct)
  const [isPhotoPopoverOpen, setIsPhotoPopoverOpen] = useState(false)

  const imageUrl = product.processed_image_url || product.scraped_image_url || COMING_SOON_URL
  const isFailed = product.scrape_failed || imageUrl === COMING_SOON_URL

  const handlePhotoUpdate = useCallback((updated: Product) => {
    setProduct(updated)
    onProductUpdate?.(updated)
  }, [onProductUpdate])

  const handleCommit = useCallback(async (field: keyof ProductPatchBody, newValue: string) => {
    const prevValue = product[field as keyof Product] as string | undefined
    if (newValue === (prevValue ?? '')) return
    setProduct(p => ({ ...p, [field]: newValue || undefined }))
    try {
      const updated = await patchProduct(campaignId, product.id, { [field]: newValue })
      setProduct(updated)
      onProductUpdate?.(updated)
    } catch {
      setProduct(p => ({ ...p, [field]: prevValue }))
      showToast('Failed to save change', 'error')
      throw new Error('patch failed')
    }
  }, [campaignId, product, onProductUpdate])

  return (
    <div
      className={`bg-neutral-0 rounded-lg border flex flex-col overflow-hidden ${
        isFailed ? 'border-error-600' : 'border-neutral-200'
      }`}
    >
      {/* Photo (clickable to edit) */}
      <button
        type="button"
        onClick={() => setIsPhotoPopoverOpen(true)}
        className="aspect-square bg-neutral-50 flex items-center justify-center overflow-hidden w-full relative group"
        aria-label={`Edit photo for SKU ${product.sku}`}
      >
        <img
          src={imageUrl}
          alt={product.scraped_name || product.sku}
          className="w-full h-full object-contain"
        />
        <div className="absolute inset-0 bg-neutral-900/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-neutral-0 text-small font-medium">Edit photo</span>
        </div>
      </button>

      <ImageEditPopover
        isOpen={isPhotoPopoverOpen}
        onClose={() => setIsPhotoPopoverOpen(false)}
        campaignId={campaignId}
        productId={product.id}
        onSuccess={handlePhotoUpdate}
      />

      {/* Fields */}
      <div className="p-3 flex flex-col gap-2">
        {/* Description */}
        <div className="flex flex-col gap-0.5">
          <span className="text-small text-neutral-400">Description</span>
          <div className="line-clamp-2 overflow-hidden">
            <InlineTextField
              value={product.scraped_name}
              onCommit={(v) => handleCommit('scraped_name', v)}
              ariaLabel={`Edit description for SKU ${product.sku}`}
            />
          </div>
        </div>

        {/* Price */}
        <div className="flex flex-col gap-0.5">
          <span className="text-small text-neutral-400">Price</span>
          <InlineTextField
            value={product.formatted_price}
            onCommit={(v) => handleCommit('formatted_price', v)}
            ariaLabel={`Edit price for SKU ${product.sku}`}
          />
        </div>

        {/* Discount */}
        <div className="flex flex-col gap-0.5">
          <span className="text-small text-neutral-400">Discount</span>
          <InlineTextField
            value={product.discount}
            onCommit={(v) => handleCommit('discount', v)}
            ariaLabel={`Edit discount for SKU ${product.sku}`}
          />
        </div>

        {/* Pack of */}
        <div className="flex flex-col gap-0.5">
          <span className="text-small text-neutral-400">Pack of</span>
          <InlineTextField
            value={product.pack_of}
            onCommit={(v) => handleCommit('pack_of', v)}
            ariaLabel={`Edit pack of for SKU ${product.sku}`}
          />
        </div>

        {/* Quantity */}
        <div className="flex flex-col gap-0.5">
          <span className="text-small text-neutral-400">Quantity</span>
          <InlineTextField
            value={product.quantity}
            onCommit={(v) => handleCommit('quantity', v)}
            ariaLabel={`Edit quantity for SKU ${product.sku}`}
          />
        </div>

        {/* SKU */}
        <span className="text-small text-neutral-400 mt-1">SKU: {product.sku}</span>
      </div>
    </div>
  )
}
