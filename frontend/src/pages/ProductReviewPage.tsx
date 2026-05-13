import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCampaign, getProducts, completeReview, type Campaign, type Product } from '../lib/api'
import { TopBar } from '../components/layout/TopBar'
import { ProductCard } from '../components/review/ProductCard'
import { showToast } from '../components/ui/Toast'

export function ProductReviewPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isProceeding, setIsProceeding] = useState(false)

  const handleProductUpdate = useCallback((updated: Product) => {
    setProducts(prev => prev.map(p => p.id === updated.id ? updated : p))
  }, [])

  const load = useCallback(async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const [camp, prods] = await Promise.all([getCampaign(id), getProducts(id)])
      setCampaign(camp)
      setProducts(prods)
    } catch {
      showToast('Failed to load campaign', 'error')
      navigate('/campaigns')
    } finally {
      setIsLoading(false)
    }
  }, [id, navigate])

  useEffect(() => {
    load()
  }, [load])

  const handleProceed = useCallback(async () => {
    if (!id) return
    setIsProceeding(true)
    try {
      await completeReview(id)
      navigate(`/campaigns/${id}`, { replace: true })
    } catch {
      showToast('Failed to complete review', 'error')
      setIsProceeding(false)
    }
  }, [id, navigate])

  if (isLoading) {
    return (
      <div className="flex flex-col h-screen bg-neutral-50">
        <TopBar
          breadcrumbs={[{ label: 'Campaigns', href: '/campaigns' }, { label: 'Review' }]}
        />
        <div className="flex-1 flex items-center justify-center">
          <span className="text-body text-neutral-400">Loading products…</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-neutral-50">
      {/* Top bar */}
      <TopBar
        breadcrumbs={[
          { label: 'Campaigns', href: '/campaigns' },
          { label: campaign?.name ?? '…', href: `/campaigns/${id}` },
          { label: 'Review' },
        ]}
        campaignStatus={campaign?.status}
      />

      {/* Sticky header bar */}
      <div className="sticky top-0 z-10 bg-neutral-0 border-b border-neutral-200 px-6 py-4 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-heading-3 text-neutral-900">Review products before sending</h1>
          <p className="text-small text-neutral-500 mt-0.5">{products.length} product{products.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          type="button"
          onClick={handleProceed}
          disabled={isProceeding}
          className="px-4 py-2 rounded-md bg-brand-primary text-neutral-0 text-body-strong hover:bg-brand-primary-hover transition-colors disabled:opacity-50 flex-shrink-0"
        >
          {isProceeding ? 'Saving…' : 'Proceed to Emailer'}
        </button>
      </div>

      {/* Product grid */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {products.length === 0 ? (
          <div className="flex items-center justify-center h-48">
            <span className="text-body text-neutral-400">No products yet — sync a sheet first.</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {products.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                campaignId={id!}
                onProductUpdate={handleProductUpdate}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
