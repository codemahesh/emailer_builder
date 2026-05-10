import axios, { AxiosError } from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor: handle 401 globally
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      // Dispatch a custom event so AuthContext can react
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    return Promise.reject(error)
  },
)

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface LoginCredentials {
  username: string // FastAPI-Users uses "username" for email in form data
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export async function loginRequest(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const formData = new URLSearchParams()
  formData.append('username', email)
  formData.append('password', password)

  const response = await api.post<LoginResponse>('/auth/jwt/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return response.data
}

export async function logoutRequest(): Promise<void> {
  await api.post('/auth/jwt/logout')
}

export interface UserRead {
  id: string
  email: string
  is_active: boolean
  is_superuser: boolean
  is_verified: boolean
  role: 'editor' | 'reviewer' | 'admin'
}

export async function getMeRequest(): Promise<UserRead> {
  const response = await api.get<UserRead>('/auth/me')
  return response.data
}

// ─── Campaigns ───────────────────────────────────────────────────────────────

export type CampaignStatus = 'draft' | 'in_review' | 'approved'

export interface Campaign {
  id: string
  name: string
  sheet_url: string
  owner_id: string
  status: CampaignStatus
  created_at: string
  updated_at: string
  owner: {
    id: string
    email: string
  } | null
}

export interface CampaignListResponse {
  items: Campaign[]
  total: number
}

export interface CreateCampaignPayload {
  name: string
  sheet_url?: string
}

export async function listCampaigns(params?: {
  status?: CampaignStatus
  skip?: number
  limit?: number
  show_archived?: boolean
}): Promise<CampaignListResponse> {
  const response = await api.get<CampaignListResponse>('/campaigns', {
    params,
  })
  return response.data
}

export async function createCampaign(
  payload: CreateCampaignPayload,
): Promise<Campaign> {
  const response = await api.post<Campaign>('/campaigns', payload)
  return response.data
}

export async function getCampaign(id: string): Promise<Campaign> {
  const response = await api.get<Campaign>(`/campaigns/${id}`)
  return response.data
}

export async function updateCampaign(
  id: string,
  payload: Partial<Pick<Campaign, 'name' | 'sheet_url' | 'status'>>,
): Promise<Campaign> {
  const response = await api.patch<Campaign>(`/campaigns/${id}`, payload)
  return response.data
}

export async function deleteCampaign(id: string): Promise<void> {
  await api.delete(`/campaigns/${id}`)
}

// ─── Sync ─────────────────────────────────────────────────────────────────────

export interface SyncStatus {
  status: 'queued' | 'running' | 'completed' | 'failed' | 'partial' | 'idle'
  total: number
  processed: number
  failed: number
  last_synced?: string
  error_message?: string
}

// ─── Sheet Verify ─────────────────────────────────────────────────────────────

export interface VerifyResponse {
  ok: boolean
  error_code: 'INVALID_URL' | 'NOT_FOUND' | 'NOT_SHARED' | 'EMPTY_SHEET' | 'MISSING_COLUMNS' | null
  headers_found: string[]
  missing_columns: string[]
  row_count: number
  sheet_title: string
  tab_count: number
}

export const verifySheet = (
  campaignId: string,
  sheetUrl: string,
): Promise<VerifyResponse> =>
  api
    .post(`/campaigns/${campaignId}/sheet/verify`, { sheet_url: sheetUrl })
    .then((r) => r.data)

// ─── Import (Update List) ─────────────────────────────────────────────────────

export interface ImportPreflightResponse {
  added: number
  removed: number
  updated: number
  unchanged: number
  rescrape_count: number
  has_changes: boolean
}

export interface ImportCommitResponse {
  job_id: string
  status: string
}

export const importSheetPreflight = (campaignId: string): Promise<ImportPreflightResponse> =>
  api.post(`/campaigns/${campaignId}/sheet/import`, { phase: 'preflight' }).then((r) => r.data)

export const importSheetCommit = (campaignId: string): Promise<ImportCommitResponse> =>
  api.post(`/campaigns/${campaignId}/sheet/import`, { phase: 'commit' }).then((r) => r.data)

// ─── File Upload ─────────────────────────────────────────────────────────────

export interface UploadResponse {
  ok: boolean
  error_code: 'INVALID_TYPE' | 'FILE_TOO_LARGE' | 'TOO_MANY_ROWS' | 'PARSE_ERROR' | 'EMPTY_SHEET' | 'MISSING_COLUMNS' | null
  headers_found: string[]
  missing_columns: string[]
  row_count: number
  version_id: string | null
  imported_count: number
}

export const uploadSheetFile = (
  campaignId: string,
  file: File,
  signal?: AbortSignal,
): Promise<UploadResponse> => {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/campaigns/${campaignId}/sheet/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    signal,
  }).then((r) => r.data)
}

// ─── Sheet Preview ────────────────────────────────────────────────────────────

export interface SheetPreviewResponse {
  version: number
  fetched_at: string
  row_count: number
  headers: string[]
  rows: Record<string, string>[]
  has_more: boolean
  offset: number
  limit: number
}

export const getSheetPreview = (
  campaignId: string,
  params: { version?: string; limit?: number; offset?: number } = {},
): Promise<SheetPreviewResponse> =>
  api
    .get(`/campaigns/${campaignId}/sheet/preview`, {
      params: { version: params.version ?? 'latest', limit: params.limit ?? 50, offset: params.offset ?? 0 },
    })
    .then((r) => r.data)

export const startFullSync = (
  campaignId: string,
): Promise<{ job_id: string; status: string }> =>
  api.post(`/campaigns/${campaignId}/sync/full`).then((r) => r.data)

export const getSyncStatus = (campaignId: string): Promise<SyncStatus> =>
  api.get(`/campaigns/${campaignId}/sync/status`).then((r) => r.data)

// ─── Products ─────────────────────────────────────────────────────────────────

export interface Product {
  id: string
  campaign_id: string
  section_id?: string
  sku: string
  product_link: string
  priority: 'high' | 'medium' | 'low'
  raw_price?: string
  formatted_price?: string
  utm_campaign?: string
  utm_stitched?: string
  button_name?: string
  scraped_name?: string
  scraped_image_url?: string
  processed_image_url?: string
  scrape_failed: boolean
  position: number
  created_at: string
  updated_at: string
}

export const getProducts = (campaignId: string): Promise<Product[]> =>
  api.get(`/campaigns/${campaignId}/products`).then((r) => r.data)

export const replaceProductImage = (
  campaignId: string,
  productId: string,
  data: { image_url?: string } | FormData,
): Promise<Product> => {
  if (data instanceof FormData) {
    return api
      .patch(
        `/campaigns/${campaignId}/products/${productId}/replace-image`,
        data,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      .then((r) => r.data)
  }
  return api
    .patch(
      `/campaigns/${campaignId}/products/${productId}/replace-image`,
      data,
    )
    .then((r) => r.data)
}

export const revertProductImage = (
  campaignId: string,
  productId: string,
): Promise<Product> =>
  api
    .post(`/campaigns/${campaignId}/products/${productId}/revert-image`)
    .then((r) => r.data)

// ─── Render ───────────────────────────────────────────────────────────────────

export interface RenderResponse {
  html: string
  size_kb: number
  section_count: number
  product_count: number
}

// RenderResult is the canonical name used by useRender hook
export type RenderResult = RenderResponse

export const renderCampaign = (campaignId: string): Promise<RenderResult> =>
  api.post(`/campaigns/${campaignId}/render`).then((r) => r.data)

// ─── Visual Brief ─────────────────────────────────────────────────────────────

export interface VisualBrief {
  id: string
  campaign_id: string
  theme_name: string
  template_id: string | null
  background_color: string
  section_color: string
  accent_color: string
  button_color: string
  product_bg_color: string
  heading_font: string
  body_font: string
  h1_size: number
  h2_size: number
  body_size: number
  dalle_prompt: string | null
  pinned_theme_id: string | null
  use_neutral_defaults: boolean
  created_at: string
  updated_at: string
}

export interface OrchestrateResponse {
  brief: VisualBrief
  html: string
  size_kb: number
}

export const getVisualBrief = (campaignId: string): Promise<VisualBrief> =>
  api.get(`/campaigns/${campaignId}/brief`).then((r) => r.data)

export const runOrchestrator = (campaignId: string): Promise<OrchestrateResponse> =>
  api.post(`/campaigns/${campaignId}/orchestrate`).then((r) => r.data)

// ─── Sections ─────────────────────────────────────────────────────────────────

export interface Section {
  id: string
  campaign_id: string
  title: string
  position: number
  locked: boolean
  created_at: string
}

export const getSections = (campaignId: string): Promise<Section[]> =>
  api.get(`/campaigns/${campaignId}/sections`).then((r) => r.data)

export const toggleSectionLock = (
  campaignId: string,
  sectionId: string,
  locked: boolean,
): Promise<Section> =>
  api
    .patch(`/campaigns/${campaignId}/sections/${sectionId}/lock`, { locked })
    .then((r) => r.data)

// ─── Fast Sync ────────────────────────────────────────────────────────────────

export const startFastSync = (
  campaignId: string,
): Promise<{ job_id: string; status: string }> =>
  api.post(`/campaigns/${campaignId}/sync/fast`).then((r) => r.data)

// ─── Banners ──────────────────────────────────────────────────────────────────

export interface Banner {
  id: string
  campaign_id: string
  variant_index: number
  image_url: string
  is_active: boolean
  generation_status: 'pending' | 'generating' | 'ready' | 'failed'
  created_at: string
}

export const getBanners = (campaignId: string): Promise<Banner[]> =>
  api.get(`/campaigns/${campaignId}/banners`).then((r) => r.data)

export const generateBanners = (campaignId: string): Promise<Banner[]> =>
  api.post(`/campaigns/${campaignId}/banners/generate`).then((r) => r.data)

export const activateBanner = (campaignId: string, bannerId: string): Promise<Banner> =>
  api.patch(`/campaigns/${campaignId}/banners/${bannerId}/activate`).then((r) => r.data)

// ─── Templates ────────────────────────────────────────────────────────────────

export interface Template {
  id: string
  name: string
  source: string
  structural_pattern: string | null
  created_at: string
}

export const getTemplates = (): Promise<Template[]> =>
  api.get('/templates').then((r) => r.data)

export const applyTemplate = (
  campaignId: string,
  templateId: string,
): Promise<VisualBrief> =>
  api.post(`/campaigns/${campaignId}/templates/apply`, { template_id: templateId }).then((r) => r.data)

// ─── Themes ───────────────────────────────────────────────────────────────────

export interface Theme {
  id: string
  name: string
  background_color: string
  section_color: string
  accent_color: string
  button_color: string
  product_bg_color: string
  heading_font: string
  body_font: string
  h1_size: number
  h2_size: number
  body_size: number
  created_at: string
}

export const getThemes = (): Promise<Theme[]> =>
  api.get('/themes').then((r) => r.data)

export const applyTheme = (
  campaignId: string,
  themeId: string,
): Promise<VisualBrief> =>
  api.post(`/campaigns/${campaignId}/themes/apply`, { theme_id: themeId }).then((r) => r.data)

// ─── Overrides ────────────────────────────────────────────────────────────────

export interface AssetOverride {
  id: string
  campaign_id: string
  target_type: string
  target_id: string | null
  override_url: string
  created_at: string
}

export interface TextOverride {
  id: string
  campaign_id: string
  target_id: string
  field: string
  override_value: string
  created_at: string
  updated_at: string
}

export const applyAssetOverride = (
  campaignId: string,
  data: { target_type: string; target_id?: string; override_url: string },
): Promise<AssetOverride> =>
  api.post(`/campaigns/${campaignId}/overrides/asset`, data).then((r) => r.data)

export const revertAssetOverride = (
  campaignId: string,
  targetType: string,
  targetId?: string,
): Promise<void> =>
  api.delete(`/campaigns/${campaignId}/overrides/asset`, {
    params: { target_type: targetType, target_id: targetId },
  }).then(() => undefined)

export const getAssetOverrides = (campaignId: string): Promise<AssetOverride[]> =>
  api.get(`/campaigns/${campaignId}/overrides/asset`).then((r) => r.data)

export const applyTextOverride = (
  campaignId: string,
  data: { target_id: string; field: string; override_value: string },
): Promise<TextOverride> =>
  api.post(`/campaigns/${campaignId}/overrides/text`, data).then((r) => r.data)

export const getTextOverrides = (campaignId: string): Promise<TextOverride[]> =>
  api.get(`/campaigns/${campaignId}/overrides/text`).then((r) => r.data)

export const deleteTextOverride = (campaignId: string, overrideId: string): Promise<void> =>
  api.delete(`/campaigns/${campaignId}/overrides/text/${overrideId}`).then(() => undefined)

// ─── Snapshots ────────────────────────────────────────────────────────────────

export interface Snapshot {
  id: string
  campaign_id: string
  summary_chip: string
  created_at: string
}

export const getSnapshots = (campaignId: string): Promise<Snapshot[]> =>
  api.get(`/campaigns/${campaignId}/snapshots`).then((r) => r.data)

export const createSnapshot = (
  campaignId: string,
  data: { summary_chip: string; mjml_state_json: string },
): Promise<Snapshot> =>
  api.post(`/campaigns/${campaignId}/snapshots`, data).then((r) => r.data)

export const restoreSnapshot = (
  campaignId: string,
  snapshotId: string,
): Promise<Snapshot> =>
  api.post(`/campaigns/${campaignId}/snapshots/${snapshotId}/restore`).then((r) => r.data)

// ─── Audit ────────────────────────────────────────────────────────────────────

export interface AuditItem {
  check: string
  status: 'pass' | 'warn' | 'hard_stop'
  message: string
}

export interface AuditReport {
  items: AuditItem[]
  size_kb: number
  has_hard_stops: boolean
  minified_html: string
}

export const auditCampaign = (
  campaignId: string,
  html?: string,
): Promise<AuditReport> =>
  api.post(`/campaigns/${campaignId}/audit`, { html: html ?? null }).then((r) => r.data)

// ─── Review / Share ───────────────────────────────────────────────────────────

export interface ReviewToken {
  token: string
  url: string
}

export const createReviewToken = (campaignId: string): Promise<ReviewToken> =>
  api.post(`/campaigns/${campaignId}/review/share`).then((r) => r.data)

// ─── Comments ────────────────────────────────────────────────────────────────

export interface Comment {
  id: string
  campaign_id: string
  section_id: string | null
  author_name: string
  body: string
  resolved: boolean
  parent_id: string | null
  created_at: string
}

export const getCampaignComments = (campaignId: string): Promise<Comment[]> =>
  api.get(`/campaigns/${campaignId}/comments`).then((r) => r.data)

export const resolveComment = (campaignId: string, commentId: string): Promise<Comment> =>
  api.patch(`/campaigns/${campaignId}/comments/${commentId}/resolve`).then((r) => r.data)

// ─── Approvals ────────────────────────────────────────────────────────────────

export interface ApprovalEvent {
  id: string
  campaign_id: string
  reviewer_name: string
  approved_at: string
  viewport_confirmed: string
}

export const getCampaignApproval = (campaignId: string): Promise<ApprovalEvent | null> =>
  api.get(`/campaigns/${campaignId}/approval`).then((r) => r.data).catch(() => null)

// ─── Preferences ──────────────────────────────────────────────────────────────

export interface UserPreference {
  id: string
  editor_id: string
  signal_type: string
  asset_type: string
  signal_value: string
  campaign_id: string | null
  weight: number
  created_at: string
}

export const getPreferences = (): Promise<UserPreference[]> =>
  api.get('/preferences').then((r) => r.data)

export const recordPreferenceSignal = (data: {
  signal_type: string
  asset_type: string
  signal_value: string
  campaign_id?: string
  weight?: number
}): Promise<UserPreference> =>
  api.post('/preferences/signal', data).then((r) => r.data)

export const deletePreference = (preferenceId: string): Promise<void> =>
  api.delete(`/preferences/${preferenceId}`).then(() => undefined)

export const deleteAllPreferences = (): Promise<void> =>
  api.delete('/preferences').then(() => undefined)

// ─── Vibe Shift ───────────────────────────────────────────────────────────────

export interface VibeShiftPreview {
  will_regenerate: string[]
  will_preserve: {
    locked_sections: number
    manual_overrides: number
    pinned_theme: string | null
  }
  directive: string
}

export const previewVibeShift = (
  campaignId: string,
  directive: string,
): Promise<VibeShiftPreview> =>
  api.post(`/campaigns/${campaignId}/vibe-shift`, { directive }).then((r) => r.data)

export const confirmVibeShift = (
  campaignId: string,
  directive: string,
): Promise<{ brief: VisualBrief; html: string }> =>
  api.post(`/campaigns/${campaignId}/vibe-shift/confirm`, { directive }).then((r) => r.data)

// ─── Campaign actions ─────────────────────────────────────────────────────────

export const duplicateCampaign = (campaignId: string): Promise<Campaign> =>
  api.post(`/campaigns/${campaignId}/duplicate`).then((r) => r.data)

export const archiveCampaign = (campaignId: string): Promise<Campaign> =>
  api.patch(`/campaigns/${campaignId}/archive`).then((r) => r.data)

// ─── Admin users ──────────────────────────────────────────────────────────────

export interface AdminUserRead {
  id: string
  email: string
  role: 'editor' | 'reviewer' | 'admin'
  is_active: boolean
}

export const listAdminUsers = (): Promise<AdminUserRead[]> =>
  api.get('/settings/users').then((r) => r.data)

export const createAdminUser = (data: { email: string; password: string }): Promise<AdminUserRead> =>
  api.post('/settings/users', data).then((r) => r.data)

// ─── WebSocket / Quality types ────────────────────────────────────────────────

export interface QualityVerdict {
  verdict: 'pass' | 'warn' | 'fail'
  reason: string
}

export interface ImageProcessingProgress {
  type: 'image_processed' | 'sync_progress' | 'banner_ready'
  data: {
    product_id?: string
    url?: string
    verdict?: string
    reason?: string
    status?: string
    total?: number
    processed?: number
    failed?: number
    cached?: boolean
    width?: number
    height?: number
  }
}
