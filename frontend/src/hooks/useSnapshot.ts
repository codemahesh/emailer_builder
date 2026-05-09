import { useState, useCallback, useEffect, useRef } from 'react'
import { api } from '../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Snapshot {
  id: string
  campaign_id: string
  summary_chip: string
  created_at: string
}

interface UseSnapshotReturn {
  snapshots: Snapshot[]
  isLoading: boolean
  createSnapshot: (summaryChip: string, mjmlStateJson: string) => Promise<Snapshot | null>
  restoreSnapshot: (snapshotId: string) => Promise<void>
  refresh: () => void
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useSnapshot(campaignId: string | undefined): UseSnapshotReturn {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const mountedRef = useRef(true)

  const fetchSnapshots = useCallback(async () => {
    if (!campaignId) return
    setIsLoading(true)
    try {
      const response = await api.get<Snapshot[]>(`/campaigns/${campaignId}/snapshots`)
      if (mountedRef.current) {
        setSnapshots(response.data)
      }
    } catch {
      // silently ignore
    } finally {
      if (mountedRef.current) {
        setIsLoading(false)
      }
    }
  }, [campaignId])

  useEffect(() => {
    mountedRef.current = true
    fetchSnapshots()
    return () => {
      mountedRef.current = false
    }
  }, [fetchSnapshots])

  const createSnapshot = useCallback(
    async (summaryChip: string, mjmlStateJson: string): Promise<Snapshot | null> => {
      if (!campaignId) return null
      try {
        const response = await api.post<Snapshot>(`/campaigns/${campaignId}/snapshots`, {
          summary_chip: summaryChip,
          mjml_state_json: mjmlStateJson,
        })
        if (mountedRef.current) {
          setSnapshots((prev) => [response.data, ...prev])
        }
        return response.data
      } catch {
        return null
      }
    },
    [campaignId],
  )

  const restoreSnapshot = useCallback(
    async (snapshotId: string): Promise<void> => {
      if (!campaignId) return
      await api.post(`/campaigns/${campaignId}/snapshots/${snapshotId}/restore`)
      await fetchSnapshots()
    },
    [campaignId, fetchSnapshots],
  )

  const refresh = useCallback(() => {
    fetchSnapshots()
  }, [fetchSnapshots])

  return { snapshots, isLoading, createSnapshot, restoreSnapshot, refresh }
}
