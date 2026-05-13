import React, { useCallback, useEffect, useRef, useState } from 'react'

interface InlineTextFieldProps {
  value: string | null | undefined
  onCommit: (newValue: string) => Promise<void>
  ariaLabel: string
}

export function InlineTextField({ value, onCommit, ariaLabel }: InlineTextFieldProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState(value ?? '')
  const [flash, setFlash] = useState<'success' | 'error' | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isCommittingRef = useRef(false)

  useEffect(() => {
    if (!isEditing) setDraft(value ?? '')
  }, [value, isEditing])

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.select()
    }
  }, [isEditing])

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const clearDebounce = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
      debounceRef.current = null
    }
  }, [])

  const doCommit = useCallback(async (val: string) => {
    clearDebounce()
    if (isCommittingRef.current) return
    isCommittingRef.current = true
    const savedValue = value ?? ''
    setIsEditing(false)
    try {
      await onCommit(val)
      setFlash('success')
      setTimeout(() => setFlash(null), 200)
    } catch {
      setDraft(savedValue)
      setFlash('error')
      setTimeout(() => setFlash(null), 1500)
    } finally {
      isCommittingRef.current = false
    }
  }, [clearDebounce, onCommit, value])

  const handleClick = useCallback(() => {
    setDraft(value ?? '')
    setIsEditing(true)
  }, [value])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value
    setDraft(v)
    clearDebounce()
    debounceRef.current = setTimeout(() => doCommit(v), 400)
  }, [clearDebounce, doCommit])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      doCommit(draft)
    } else if (e.key === 'Escape') {
      e.preventDefault()
      clearDebounce()
      setDraft(value ?? '')
      setIsEditing(false)
    }
  }, [clearDebounce, doCommit, draft, value])

  const handleBlur = useCallback(() => {
    if (!isCommittingRef.current) doCommit(draft)
  }, [doCommit, draft])

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={draft}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        aria-label={ariaLabel}
        className="w-full text-body text-neutral-800 px-1 py-0.5 rounded border border-brand-primary ring-1 ring-brand-primary outline-none bg-neutral-0"
      />
    )
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={ariaLabel}
      className={[
        'w-full text-left px-1 py-0.5 rounded transition-colors cursor-text min-h-[1.5rem]',
        flash === 'error' ? 'ring-1 ring-error-600' : 'hover:bg-neutral-100',
      ].join(' ')}
    >
      {flash === 'success' ? (
        <span className="text-success-600 text-body">✓</span>
      ) : draft ? (
        <span className="text-body text-neutral-800">{draft}</span>
      ) : (
        <span className="text-body text-neutral-400">—</span>
      )}
    </button>
  )
}
