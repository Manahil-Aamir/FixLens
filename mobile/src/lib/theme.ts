import type { Ionicons } from '@expo/vector-icons'
import type { Risk } from './types'

export const colors = {
  bg: '#111827',
  surface: '#1F2937',
  border: '#374151',
  accent: '#06B6D4',
  accentLight: '#A5F3FC',
  text: '#F9FAFB',
  textMuted: '#9CA3AF',
  success: '#22C55E',
  warning: '#F59E0B',
  critical: '#EF4444',
  onAccent: '#06222A',
}

export const radius = { card: 16, button: 14, pill: 999 }

// Severity is always shown as icon + text, never color alone.
export const RISK_STYLE: Record<
  Risk,
  { label: string; icon: keyof typeof Ionicons.glyphMap; color: string }
> = {
  low: { label: 'Low risk', icon: 'checkmark-circle', color: colors.success },
  medium: { label: 'Caution', icon: 'alert-circle', color: colors.warning },
  high: { label: 'High risk', icon: 'warning', color: colors.critical },
  stop: { label: 'Stop', icon: 'ban', color: colors.critical },
}
