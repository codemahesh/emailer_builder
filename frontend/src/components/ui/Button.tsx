import React from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
  fullWidth?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: [
    'bg-brand-primary text-neutral-0',
    'hover:bg-brand-primary-hover',
    'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed',
  ].join(' '),
  secondary: [
    'bg-neutral-0 text-neutral-800 border border-neutral-200',
    'hover:bg-neutral-50 hover:border-neutral-400',
    'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed',
  ].join(' '),
  ghost: [
    'bg-transparent text-neutral-600',
    'hover:bg-neutral-100 hover:text-neutral-800',
    'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed',
  ].join(' '),
  danger: [
    'bg-danger-600 text-neutral-0',
    'hover:bg-red-700',
    'focus-visible:ring-2 focus-visible:ring-danger-600 focus-visible:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed',
  ].join(' '),
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-small-strong rounded-sm',
  md: 'h-9 px-4 text-body-strong rounded-md',
  lg: 'h-11 px-6 text-body-strong rounded-md',
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  fullWidth = false,
  leftIcon,
  rightIcon,
  children,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={[
        'inline-flex items-center justify-center gap-2 font-semibold transition-colors duration-150 outline-none',
        variantClasses[variant],
        sizeClasses[size],
        fullWidth ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        leftIcon
      )}
      {children}
      {!isLoading && rightIcon}
    </button>
  )
}
