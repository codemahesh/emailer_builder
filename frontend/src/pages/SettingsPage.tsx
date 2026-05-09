import React, { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { listAdminUsers, createAdminUser, type AdminUserRead } from '../lib/api'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Skeleton } from '../components/ui/Skeleton'
import { showToast } from '../components/ui/Toast'
import { useAuth } from '../hooks/useAuth'

// ── Types ─────────────────────────────────────────────────────────────────────

interface GlobalSettings {
  id: string
  header_html: string
  footer_html: string
  brand_primary_color: string
  brand_secondary_color: string
  heading_font: string
  body_font: string
  global_utm_prefix: string
  updated_at: string
}

interface KeywordMapping {
  id: string
  keyword: string
  icon_name: string
  position: string
}

type TabId = 'headers' | 'brand' | 'keywords' | 'utm' | 'users'

const TABS: { id: TabId; label: string; adminOnly?: boolean }[] = [
  { id: 'headers', label: 'Headers & Footers' },
  { id: 'brand', label: 'Brand Tokens' },
  { id: 'keywords', label: 'Keyword Mappings' },
  { id: 'utm', label: 'UTM Prefix' },
  { id: 'users', label: 'Users', adminOnly: true },
]

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SettingsSkeleton() {
  return (
    <div className="flex flex-col gap-5" aria-busy="true">
      <Skeleton className="w-full h-36 rounded-md" />
      <Skeleton className="w-full h-36 rounded-md" />
    </div>
  )
}

// ── Tab: Headers & Footers ────────────────────────────────────────────────────

interface HeadersTabProps {
  settings: GlobalSettings
  onChange: (patch: Partial<GlobalSettings>) => void
}

function HeadersTab({ settings, onChange }: HeadersTabProps) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <label htmlFor="header-html" className="text-small-strong text-neutral-800">Header HTML</label>
        <textarea
          id="header-html"
          value={settings.header_html}
          onChange={(e) => onChange({ header_html: e.target.value })}
          rows={6}
          className="w-full px-3 py-2 rounded-md border border-neutral-200 bg-neutral-0 text-body text-neutral-800 font-mono placeholder:text-neutral-400 resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          placeholder="<!-- header HTML here -->"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="footer-html" className="text-small-strong text-neutral-800">Footer HTML</label>
        <textarea
          id="footer-html"
          value={settings.footer_html}
          onChange={(e) => onChange({ footer_html: e.target.value })}
          rows={6}
          className="w-full px-3 py-2 rounded-md border border-neutral-200 bg-neutral-0 text-body text-neutral-800 font-mono placeholder:text-neutral-400 resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          placeholder="<!-- footer HTML here -->"
        />
        <p className="text-small text-neutral-400 mt-1">
          CleverTap tags (<code className="font-mono">{'{{unsubscribe_link}}'}</code>,{' '}
          <code className="font-mono">{'{{view_in_browser}}'}</code>) are included in the default footer.
        </p>
      </div>
    </div>
  )
}

// ── Tab: Brand Tokens ─────────────────────────────────────────────────────────

interface BrandTabProps {
  settings: GlobalSettings
  onChange: (patch: Partial<GlobalSettings>) => void
}

function ColorInput({
  id,
  label,
  value,
  onChange,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-small-strong text-neutral-800">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value || '#000000'}
          onChange={(e) => onChange(e.target.value)}
          className="w-9 h-9 rounded border border-neutral-200 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          aria-label={`${label} color picker`}
        />
        <input
          id={id}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          maxLength={7}
          placeholder="#000000"
          className="h-9 w-32 px-3 rounded-md border border-neutral-200 bg-neutral-0 text-body text-neutral-800 font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
        />
      </div>
    </div>
  )
}

function BrandTab({ settings, onChange }: BrandTabProps) {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <ColorInput
          id="brand-primary-color"
          label="Primary Color"
          value={settings.brand_primary_color}
          onChange={(v) => onChange({ brand_primary_color: v })}
        />
        <ColorInput
          id="brand-secondary-color"
          label="Secondary Color"
          value={settings.brand_secondary_color}
          onChange={(v) => onChange({ brand_secondary_color: v })}
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div className="flex flex-col gap-1">
          <label htmlFor="heading-font" className="text-small-strong text-neutral-800">Heading Font</label>
          <input
            id="heading-font"
            type="text"
            value={settings.heading_font}
            onChange={(e) => onChange({ heading_font: e.target.value })}
            placeholder="e.g. Inter, sans-serif"
            className="h-9 px-3 rounded-md border border-neutral-200 bg-neutral-0 text-body text-neutral-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="body-font" className="text-small-strong text-neutral-800">Body Font</label>
          <input
            id="body-font"
            type="text"
            value={settings.body_font}
            onChange={(e) => onChange({ body_font: e.target.value })}
            placeholder="e.g. Georgia, serif"
            className="h-9 px-3 rounded-md border border-neutral-200 bg-neutral-0 text-body text-neutral-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          />
        </div>
      </div>
      {/* Font preview */}
      <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 flex flex-col gap-2">
        <p
          className="text-heading-2 text-neutral-800"
          style={{ fontFamily: settings.heading_font || undefined }}
        >
          The quick brown fox
        </p>
        <p
          className="text-body text-neutral-600"
          style={{ fontFamily: settings.body_font || undefined }}
        >
          Jumps over the lazy dog. Body text preview at 14px regular weight.
        </p>
        <div className="flex gap-3 mt-1">
          <div
            className="w-6 h-6 rounded-full border border-neutral-200"
            style={{ background: settings.brand_primary_color || '#2E5BFF' }}
            title="Primary color"
          />
          <div
            className="w-6 h-6 rounded-full border border-neutral-200"
            style={{ background: settings.brand_secondary_color || '#ccc' }}
            title="Secondary color"
          />
        </div>
      </div>
    </div>
  )
}

// ── Tab: Keyword Mappings ─────────────────────────────────────────────────────

interface KeywordsTabProps {
  mappings: KeywordMapping[]
  onMappingsChange: (mappings: KeywordMapping[]) => void
}

interface EditingRow {
  keyword: string
  icon_name: string
  position: string
}

function KeywordsTab({ mappings, onMappingsChange }: KeywordsTabProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingRow, setEditingRow] = useState<EditingRow>({ keyword: '', icon_name: '', position: '' })
  const [newRow, setNewRow] = useState<EditingRow>({ keyword: '', icon_name: '', position: '' })
  const [isAdding, setIsAdding] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const startEdit = (m: KeywordMapping) => {
    setEditingId(m.id)
    setEditingRow({ keyword: m.keyword, icon_name: m.icon_name, position: m.position })
  }

  const saveEdit = async (id: string) => {
    try {
      const res = await api.patch<KeywordMapping>(`/settings/keyword-mappings/${id}`, editingRow)
      onMappingsChange(mappings.map((m) => (m.id === id ? res.data : m)))
      showToast('Mapping updated', 'success')
    } catch {
      showToast('Failed to update mapping', 'error')
    } finally {
      setEditingId(null)
    }
  }

  const deleteMapping = async (id: string) => {
    setDeletingId(id)
    try {
      await api.delete(`/settings/keyword-mappings/${id}`)
      onMappingsChange(mappings.filter((m) => m.id !== id))
      showToast('Mapping deleted', 'success')
    } catch {
      showToast('Failed to delete mapping', 'error')
    } finally {
      setDeletingId(null)
    }
  }

  const addMapping = async () => {
    if (!newRow.keyword.trim()) return
    setIsAdding(true)
    try {
      const res = await api.post<KeywordMapping>('/settings/keyword-mappings', newRow)
      onMappingsChange([...mappings, res.data])
      setNewRow({ keyword: '', icon_name: '', position: '' })
      showToast('Mapping added', 'success')
    } catch {
      showToast('Failed to add mapping', 'error')
    } finally {
      setIsAdding(false)
    }
  }

  const cellCls =
    'h-8 px-2 rounded border border-neutral-200 bg-neutral-0 text-body text-neutral-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1'

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto rounded-lg border border-neutral-200">
        <table className="w-full text-body">
          <thead>
            <tr className="bg-neutral-50 border-b border-neutral-200">
              <th className="text-left px-4 py-2 text-small-strong text-neutral-600 w-1/3">Keyword</th>
              <th className="text-left px-4 py-2 text-small-strong text-neutral-600 w-1/3">Icon Name</th>
              <th className="text-left px-4 py-2 text-small-strong text-neutral-600 w-1/4">Position</th>
              <th className="px-4 py-2 text-small-strong text-neutral-600 w-[100px]">Actions</th>
            </tr>
          </thead>
          <tbody>
            {mappings.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-body text-neutral-400">
                  No keyword mappings yet.
                </td>
              </tr>
            )}
            {mappings.map((m) => (
              <tr
                key={m.id}
                className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors"
              >
                {editingId === m.id ? (
                  <>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editingRow.keyword}
                        onChange={(e) => setEditingRow((r) => ({ ...r, keyword: e.target.value }))}
                        className={`${cellCls} w-full`}
                        autoFocus
                        onBlur={() => saveEdit(m.id)}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editingRow.icon_name}
                        onChange={(e) => setEditingRow((r) => ({ ...r, icon_name: e.target.value }))}
                        className={`${cellCls} w-full`}
                        onBlur={() => saveEdit(m.id)}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editingRow.position}
                        onChange={(e) => setEditingRow((r) => ({ ...r, position: e.target.value }))}
                        className={`${cellCls} w-full`}
                        onBlur={() => saveEdit(m.id)}
                      />
                    </td>
                    <td className="px-4 py-2" />
                  </>
                ) : (
                  <>
                    <td className="px-4 py-2 text-neutral-800">{m.keyword}</td>
                    <td className="px-4 py-2 text-neutral-600">{m.icon_name}</td>
                    <td className="px-4 py-2 text-neutral-600">{m.position}</td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-1 justify-center">
                        <button
                          type="button"
                          onClick={() => startEdit(m)}
                          className="px-2 py-1 text-small text-brand-primary hover:text-brand-primary-hover transition-colors rounded focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
                          aria-label={`Edit mapping: ${m.keyword}`}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteMapping(m.id)}
                          disabled={deletingId === m.id}
                          className="px-2 py-1 text-small text-danger-600 hover:text-red-700 transition-colors rounded focus-visible:ring-2 focus-visible:ring-danger-600 focus-visible:ring-offset-1 disabled:opacity-50"
                          aria-label={`Delete mapping: ${m.keyword}`}
                        >
                          {deletingId === m.id ? '…' : 'Delete'}
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}

            {/* Add row */}
            <tr className="bg-neutral-50">
              <td className="px-4 py-2">
                <input
                  type="text"
                  value={newRow.keyword}
                  onChange={(e) => setNewRow((r) => ({ ...r, keyword: e.target.value }))}
                  placeholder="New keyword"
                  className={`${cellCls} w-full`}
                />
              </td>
              <td className="px-4 py-2">
                <input
                  type="text"
                  value={newRow.icon_name}
                  onChange={(e) => setNewRow((r) => ({ ...r, icon_name: e.target.value }))}
                  placeholder="Icon name"
                  className={`${cellCls} w-full`}
                />
              </td>
              <td className="px-4 py-2">
                <input
                  type="text"
                  value={newRow.position}
                  onChange={(e) => setNewRow((r) => ({ ...r, position: e.target.value }))}
                  placeholder="Position"
                  className={`${cellCls} w-full`}
                />
              </td>
              <td className="px-4 py-2 text-center">
                <button
                  type="button"
                  onClick={addMapping}
                  disabled={!newRow.keyword.trim() || isAdding}
                  className="px-2 py-1 text-small-strong text-brand-primary hover:text-brand-primary-hover transition-colors rounded disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
                  aria-label="Add mapping"
                >
                  {isAdding ? '…' : '+ Add'}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tab: UTM Prefix ───────────────────────────────────────────────────────────

interface UtmTabProps {
  settings: GlobalSettings
  onChange: (patch: Partial<GlobalSettings>) => void
}

function UtmTab({ settings, onChange }: UtmTabProps) {
  return (
    <div className="flex flex-col gap-2 max-w-sm">
      <label htmlFor="global-utm-prefix" className="text-small-strong text-neutral-800">Global UTM Prefix</label>
      <input
        id="global-utm-prefix"
        type="text"
        value={settings.global_utm_prefix}
        onChange={(e) => onChange({ global_utm_prefix: e.target.value })}
        placeholder="e.g. summer_sale"
        className="h-9 px-3 rounded-md border border-neutral-200 bg-neutral-0 text-body text-neutral-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
      />
      <p className="text-small text-neutral-400">
        Prepended to all product UTM_Campaign values. e.g. <code className="font-mono">summer_sale</code>
      </p>
    </div>
  )
}

// ── Tab: Users (admin only) ───────────────────────────────────────────────────

function UsersTab() {
  const [users, setUsers] = useState<AdminUserRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  const loadUsers = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await listAdminUsers()
      setUsers(data)
    } catch {
      showToast('Failed to load users', 'error')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newEmail.trim() || !newPassword.trim()) return
    setIsCreating(true)
    try {
      const user = await createAdminUser({ email: newEmail.trim(), password: newPassword })
      setUsers((prev) => [...prev, user])
      setNewEmail('')
      setNewPassword('')
      showToast(`Reviewer account created for ${user.email}`, 'success')
    } catch {
      showToast('Failed to create user', 'error')
    } finally {
      setIsCreating(false)
    }
  }

  if (isLoading) return <SettingsSkeleton />

  return (
    <div className="flex flex-col gap-6">
      {/* Users list */}
      <div className="overflow-x-auto rounded-lg border border-neutral-200">
        <table className="w-full text-body">
          <thead>
            <tr className="bg-neutral-50 border-b border-neutral-200">
              <th className="text-left px-4 py-2 text-small-strong text-neutral-600">Email</th>
              <th className="text-left px-4 py-2 text-small-strong text-neutral-600">Role</th>
              <th className="text-left px-4 py-2 text-small-strong text-neutral-600">Status</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-body text-neutral-400">
                  No users yet.
                </td>
              </tr>
            )}
            {users.map((u) => (
              <tr key={u.id} className="border-b border-neutral-100">
                <td className="px-4 py-2 text-neutral-800">{u.email}</td>
                <td className="px-4 py-2">
                  <span className={[
                    'text-caption px-2 py-0.5 rounded-full font-medium',
                    u.role === 'admin' ? 'bg-error-50 text-error-600' :
                    u.role === 'editor' ? 'bg-brand-primary-soft text-brand-primary' :
                    'bg-neutral-100 text-neutral-600',
                  ].join(' ')}>
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-2 text-neutral-500 text-small">
                  {u.is_active ? 'Active' : 'Inactive'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create reviewer form */}
      <div className="border border-neutral-200 rounded-lg p-4 flex flex-col gap-4">
        <h3 className="text-small-strong text-neutral-800">Create Reviewer Account</h3>
        <form onSubmit={handleCreate} className="flex flex-col gap-3">
          <Input
            label="Email"
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            placeholder="reviewer@example.com"
            required
          />
          <Input
            label="Password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Minimum 8 characters"
            required
          />
          <div className="flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isCreating}
              disabled={!newEmail.trim() || !newPassword.trim() || isCreating}
            >
              Create Reviewer
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

const EMPTY_SETTINGS: GlobalSettings = {
  id: '',
  header_html: '',
  footer_html: '',
  brand_primary_color: '#2E5BFF',
  brand_secondary_color: '#cccccc',
  heading_font: '',
  body_font: '',
  global_utm_prefix: '',
  updated_at: '',
}

export function SettingsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [activeTab, setActiveTab] = useState<TabId>('headers')
  const [isLoading, setIsLoading] = useState(true)

  const [savedSettings, setSavedSettings] = useState<GlobalSettings>(EMPTY_SETTINGS)
  const [settings, setSettings] = useState<GlobalSettings>(EMPTY_SETTINGS)

  const [mappings, setMappings] = useState<KeywordMapping[]>([])

  const [isSaving, setIsSaving] = useState(false)

  const isDirty =
    activeTab !== 'keywords' &&
    activeTab !== 'users' &&
    JSON.stringify(settings) !== JSON.stringify(savedSettings)

  // ── Load ────────────────────────────────────────────────────────────────────

  const loadSettings = useCallback(async () => {
    setIsLoading(true)
    try {
      const [settingsRes, mappingsRes] = await Promise.all([
        api.get<GlobalSettings>('/settings'),
        api.get<KeywordMapping[]>('/settings/keyword-mappings'),
      ])
      setSavedSettings(settingsRes.data)
      setSettings(settingsRes.data)
      setMappings(mappingsRes.data)
    } catch {
      showToast('Failed to load settings', 'error')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleChange = (patch: Partial<GlobalSettings>) => {
    setSettings((prev) => ({ ...prev, ...patch }))
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const res = await api.patch<GlobalSettings>('/settings', settings)
      setSavedSettings(res.data)
      setSettings(res.data)
      showToast('Settings saved', 'success')
    } catch {
      showToast('Failed to save settings', 'error')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDiscard = () => {
    setSettings(savedSettings)
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex flex-col bg-neutral-50 pb-20">
      <TopBar breadcrumbs={[{ label: 'Settings' }]} />

      <div className="max-w-[720px] w-full mx-auto px-4 sm:px-6 py-8 flex flex-col gap-6 flex-1">
        <h1 className="text-heading-1 text-neutral-900">Settings</h1>

        {/* Tab bar */}
        <div className="flex gap-0 border-b border-neutral-200 -mb-6">
          {TABS.filter((tab) => !tab.adminOnly || isAdmin).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={[
                'px-4 py-2.5 text-body-strong border-b-2 transition-colors duration-150 whitespace-nowrap',
                activeTab === tab.id
                  ? 'border-brand-primary text-brand-primary'
                  : 'border-transparent text-neutral-600 hover:text-neutral-800 hover:border-neutral-200',
              ].join(' ')}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="bg-neutral-0 rounded-lg border border-neutral-200 p-6 mt-8">
          {isLoading && activeTab !== 'users' ? (
            <SettingsSkeleton />
          ) : (
            <>
              {activeTab === 'headers' && (
                <HeadersTab settings={settings} onChange={handleChange} />
              )}
              {activeTab === 'brand' && (
                <BrandTab settings={settings} onChange={handleChange} />
              )}
              {activeTab === 'keywords' && (
                <KeywordsTab mappings={mappings} onMappingsChange={setMappings} />
              )}
              {activeTab === 'utm' && (
                <UtmTab settings={settings} onChange={handleChange} />
              )}
              {activeTab === 'users' && isAdmin && (
                <UsersTab />
              )}
              {activeTab === 'users' && !isAdmin && (
                <p className="text-body text-neutral-400 text-center py-8">
                  Admin access required.
                </p>
              )}
            </>
          )}
        </div>
      </div>

      {/* Save bar */}
      {isDirty && (
        <div className="fixed bottom-0 left-0 right-0 bg-neutral-0 border-t border-neutral-200 px-6 py-3 shadow-elev-overlay flex items-center justify-between z-30">
          <span className="text-small text-neutral-400">You have unsaved changes</span>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleDiscard}
              disabled={isSaving}
            >
              Discard changes
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              isLoading={isSaving}
              onClick={handleSave}
            >
              Save changes
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
