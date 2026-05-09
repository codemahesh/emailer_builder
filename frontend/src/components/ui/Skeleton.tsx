import React from 'react'

interface SkeletonProps {
  className?: string
  width?: string | number
  height?: string | number
  rounded?: 'sm' | 'md' | 'lg' | 'full'
}

const roundedClasses = {
  sm:   'rounded-sm',
  md:   'rounded-md',
  lg:   'rounded-lg',
  full: 'rounded-full',
}

export function Skeleton({
  className = '',
  width,
  height,
  rounded = 'md',
}: SkeletonProps) {
  return (
    <div
      className={[
        'shimmer',
        roundedClasses[rounded],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      style={{
        width: width !== undefined ? (typeof width === 'number' ? `${width}px` : width) : undefined,
        height: height !== undefined ? (typeof height === 'number' ? `${height}px` : height) : undefined,
      }}
      aria-hidden="true"
    />
  )
}

export function CampaignCardSkeleton() {
  return (
    <div className="flex flex-col rounded-lg shadow-elev-flat border border-neutral-100 overflow-hidden bg-neutral-0 min-h-[240px]">
      {/* Thumbnail */}
      <Skeleton className="w-full h-[160px]" rounded="sm" />
      {/* Content */}
      <div className="flex flex-col gap-2 p-4">
        <Skeleton className="w-3/4 h-4" />
        <Skeleton className="w-1/3 h-3" rounded="full" />
        <Skeleton className="w-1/2 h-3 mt-2" />
      </div>
    </div>
  )
}
