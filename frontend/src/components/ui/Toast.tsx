import React, { createContext, useCallback, useContext, useState } from 'react'

type ToastVariant = 'success' | 'error' | 'warn' | 'info'

interface ToastItem {
  id: string
  message: string
  variant: ToastVariant
}

interface ToastContextValue {
  showToast: (message: string, variant?: ToastVariant) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let toastCounter = 0

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const showToast = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = `toast-${++toastCounter}`
    setToasts((prev) => [...prev, { id, message, variant }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  // Expose showToast globally
  React.useEffect(() => {
    ;(window as unknown as Record<string, unknown>).__showToast = showToast
  }, [showToast])

  const variantStyles: Record<ToastVariant, string> = {
    success: 'bg-success-50 border-success-600 text-success-600',
    error:   'bg-danger-50 border-danger-600 text-danger-600',
    warn:    'bg-warn-50 border-warn-600 text-warn-600',
    info:    'bg-info-50 border-info-600 text-info-600',
  }

  const icons: Record<ToastVariant, string> = {
    success: '✓',
    error:   '✕',
    warn:    '⚠',
    info:    'ℹ',
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      <div
        className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 pointer-events-none"
        role="region"
        aria-label="Notifications"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={[
              'flex items-start gap-3 px-4 py-3 rounded-md border shadow-elev-raised',
              'min-w-[280px] max-w-[400px] pointer-events-auto',
              'animate-in slide-in-from-bottom-4 fade-in duration-200',
              variantStyles[toast.variant],
            ].join(' ')}
            role="alert"
          >
            <span className="text-body-strong flex-shrink-0 mt-0.5">
              {icons[toast.variant]}
            </span>
            <p className="text-body text-neutral-800">{toast.message}</p>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  // Fallback to the window-level showToast if not in context
  const context = useContext(ToastContext)
  const showToast = useCallback(
    (message: string, variant: ToastVariant = 'info') => {
      if (context) {
        context.showToast(message, variant)
      } else {
        const globalFn = (window as unknown as Record<string, unknown>).__showToast
        if (typeof globalFn === 'function') {
          ;(globalFn as (m: string, v: ToastVariant) => void)(message, variant)
        }
      }
    },
    [context],
  )
  return { showToast }
}

export function showToast(message: string, variant: ToastVariant = 'info') {
  const globalFn = (window as unknown as Record<string, unknown>).__showToast
  if (typeof globalFn === 'function') {
    ;(globalFn as (m: string, v: ToastVariant) => void)(message, variant)
  }
}
