import AsyncStorage from '@react-native-async-storage/async-storage'
import type { Diagnosis } from './types'

const KEY = 'fixlens.history.v1'
const MAX_ITEMS = 50

export interface QA {
  question: string
  answer: string
}

export interface HistoryExtras {
  mediaUri?: string
  mediaKind?: 'image' | 'video'
  qa?: QA[]
}

export interface HistoryItem extends HistoryExtras {
  savedAt: string
  diagnosis: Diagnosis
}

export async function loadHistory(): Promise<HistoryItem[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as HistoryItem[]) : []
  } catch {
    return []
  }
}

export async function saveToHistory(
  diagnosis: Diagnosis,
  extras: HistoryExtras = {},
): Promise<void> {
  try {
    const items = await loadHistory()
    const entry: HistoryItem = { savedAt: new Date().toISOString(), diagnosis, ...extras }
    const next = [entry, ...items.filter((i) => i.diagnosis.id !== diagnosis.id)].slice(
      0,
      MAX_ITEMS,
    )
    await AsyncStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    /* history is a convenience; never block the user */
  }
}

export async function getHistoryItem(id: string): Promise<HistoryItem | null> {
  const items = await loadHistory()
  return items.find((i) => i.diagnosis.id === id) ?? null
}

export async function clearHistory(): Promise<void> {
  try {
    await AsyncStorage.removeItem(KEY)
  } catch {
    /* ignore */
  }
}
