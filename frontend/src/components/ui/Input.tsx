import React, { useId } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftAddon?: React.ReactNode
  rightAddon?: React.ReactNode
}

export function Input({
  label,
  error,
  helperText,
  leftAddon,
  rightAddon,
  className = '',
  id: externalId,
  ...props
}: InputProps) {
  const generatedId = useId()
  const id = externalId ?? generatedId

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label
          htmlFor={id}
          className="text-small-strong text-neutral-800 select-none"
        >
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {leftAddon && (
          <span className="absolute left-3 flex items-center text-neutral-400 pointer-events-none">
            {leftAddon}
          </span>
        )}
        <input
          id={id}
          className={[
            'w-full h-9 px-3 rounded-md border text-body text-neutral-800 bg-neutral-0',
            'placeholder:text-neutral-400',
            'transition-colors duration-150',
            'focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-0 focus:border-brand-primary',
            error
              ? 'border-danger-600 bg-danger-50 focus:ring-danger-600 focus:border-danger-600'
              : 'border-neutral-200 hover:border-neutral-400',
            leftAddon ? 'pl-9' : '',
            rightAddon ? 'pr-9' : '',
            props.disabled ? 'opacity-50 cursor-not-allowed bg-neutral-100' : '',
            className,
          ]
            .filter(Boolean)
            .join(' ')}
          {...props}
        />
        {rightAddon && (
          <span className="absolute right-3 flex items-center text-neutral-400 pointer-events-none">
            {rightAddon}
          </span>
        )}
      </div>
      {error && (
        <p className="text-small text-danger-600" role="alert">
          {error}
        </p>
      )}
      {!error && helperText && (
        <p className="text-small text-neutral-400">{helperText}</p>
      )}
    </div>
  )
}
