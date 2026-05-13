import type { Product } from '../../lib/api'

const COMING_SOON_URL = '/static/coming-soon.svg'

interface ProductCardProps {
  product: Product
}

function FieldRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-small text-neutral-400">{label}</span>
      <span className="text-body text-neutral-800 break-words">
        {value || <span className="text-neutral-400">—</span>}
      </span>
    </div>
  )
}

export function ProductCard({ product }: ProductCardProps) {
  const imageUrl = product.processed_image_url || product.scraped_image_url || COMING_SOON_URL
  const isFailed = product.scrape_failed || imageUrl === COMING_SOON_URL

  return (
    <div
      className={`bg-neutral-0 rounded-lg border flex flex-col overflow-hidden ${
        isFailed ? 'border-error-600' : 'border-neutral-200'
      }`}
    >
      {/* Photo */}
      <div className="aspect-square bg-neutral-50 flex items-center justify-center overflow-hidden">
        <img
          src={imageUrl}
          alt={product.scraped_name || product.sku}
          className="w-full h-full object-contain"
        />
      </div>

      {/* Fields */}
      <div className="p-3 flex flex-col gap-2">
        {/* Description */}
        <div className="flex flex-col gap-0.5">
          <span className="text-small text-neutral-400">Description</span>
          <span className="text-body text-neutral-800 line-clamp-2">
            {product.scraped_name || <span className="text-neutral-400">—</span>}
          </span>
        </div>

        {/* Price + Discount */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-body text-neutral-800">
            {product.formatted_price || <span className="text-neutral-400">—</span>}
          </span>
          {product.discount && (
            <span className="text-small px-1.5 py-0.5 rounded-full bg-brand-primary text-neutral-0">
              {product.discount}
            </span>
          )}
        </div>

        <FieldRow label="Pack of" value={product.pack_of} />
        <FieldRow label="Quantity" value={product.quantity} />

        {/* SKU — small muted */}
        <span className="text-small text-neutral-400 mt-1">SKU: {product.sku}</span>
      </div>
    </div>
  )
}
