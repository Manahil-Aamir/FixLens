import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { Alert, useColorScheme } from 'react-native'
import type { Ionicons } from '@expo/vector-icons'
import type { ReactNode } from 'react'
import type { Risk } from './types'

export type ThemeMode = 'light' | 'dark'

export const darkcolors = {
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

export const lightcolors = {
  bg: '#F8FAFC',
  surface: '#FFFFFF',
  border: '#E2E8F0',

  accent: '#0891B2',
  accentLight: '#A5F3FC',

  text: '#0F172A',
  textMuted: '#64748B',

  success: '#16A34A',
  warning: '#D97706',
  critical: '#DC2626',

  onAccent: '#FFFFFF',
}

export type ThemeColors = typeof darkcolors

const THEME_KEY = 'fixlens.theme.v1'

const palettes: Record<ThemeMode, ThemeColors> = {
  dark: darkcolors,
  light: lightcolors,
}

interface ThemeContextValue {
  colors: ThemeColors
  mode: ThemeMode
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme()
  const [mode, setMode] = useState<ThemeMode>(systemScheme === 'light' ? 'light' : 'dark')
  const userSelected = useRef(false)

  useEffect(() => {
    let active = true
    AsyncStorage.getItem(THEME_KEY)
      .then((savedMode) => {
        if (!active || userSelected.current) return
        if (savedMode === 'light' || savedMode === 'dark') setMode(savedMode)
      })
      .catch((error: unknown) => {
        console.error('Unable to load saved theme preference.', error)
      })
    return () => {
      active = false
    }
  }, [])

  const toggleTheme = useCallback(() => {
    const nextMode = mode === 'dark' ? 'light' : 'dark'
    userSelected.current = true
    setMode(nextMode)
    AsyncStorage.setItem(THEME_KEY, nextMode).catch((error: unknown) => {
      console.error('Unable to save theme preference.', error)
      Alert.alert('Theme not saved', 'Your theme changed, but the preference could not be saved.')
    })
  }, [mode])

  return createElement(
    ThemeContext.Provider,
    { value: { colors: palettes[mode], mode, toggleTheme } },
    children,
  )
}

export function useTheme() {
  const theme = useContext(ThemeContext)
  if (!theme) throw new Error('useTheme must be used within a ThemeProvider.')
  return theme
}

export const radius = { card: 16, button: 14, pill: 999 }

// Severity is always shown as icon + text, never color alone.
export const RISK_STYLE: Record<
  Risk,
  { label: string; icon: keyof typeof Ionicons.glyphMap; color: 'success' | 'warning' | 'critical' }
> = {
  low: { label: 'Low risk', icon: 'checkmark-circle', color: 'success' },
  medium: { label: 'Caution', icon: 'alert-circle', color: 'warning' },
  high: { label: 'High risk', icon: 'warning', color: 'critical' },
  stop: { label: 'Stop', icon: 'ban', color: 'critical' },
}
