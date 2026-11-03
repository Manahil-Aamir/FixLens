import type { ReactNode } from 'react'
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type ViewStyle,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { radius, RISK_STYLE, useTheme } from './theme'
import type { Risk } from './types'

type IconName = keyof typeof Ionicons.glyphMap

export function Screen({ children, safeTop = true }: { children: ReactNode; safeTop?: boolean }) {
  const { colors } = useTheme()
  const content = (
    <ScrollView
      contentContainerStyle={{ padding: 20, gap: 16, paddingBottom: 40 }}
      keyboardShouldPersistTaps='handled'
    >
      {children}
    </ScrollView>
  )
  if (!safeTop) return <View style={{ flex: 1, backgroundColor: colors.bg }}>{content}</View>
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      {content}
    </SafeAreaView>
  )
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  const { colors } = useTheme()
  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.surface, borderColor: colors.border },
        style,
      ]}
    >
      {children}
    </View>
  )
}

export function SectionTitle({ children }: { children: ReactNode }) {
  const { colors } = useTheme()
  return <Text style={[styles.section, { color: colors.text }]}>{children}</Text>
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  icon,
  disabled,
  loading,
}: {
  title: string
  onPress: () => void
  variant?: 'primary' | 'secondary'
  icon?: IconName
  disabled?: boolean
  loading?: boolean
}) {
  const { colors } = useTheme()
  const primary = variant === 'primary'
  const fg = primary ? colors.onAccent : colors.accent
  const off = disabled || loading
  return (
    <Pressable
      onPress={onPress}
      disabled={off}
      accessibilityRole='button'
      accessibilityLabel={title}
      style={({ pressed }) => [
        styles.button,
        primary
          ? { backgroundColor: colors.accent }
          : { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: colors.accent },
        off && { opacity: 0.5 },
        pressed && { opacity: 0.85 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={20} color={fg} /> : null}
          <Text style={[styles.buttonText, { color: fg }]}>{title}</Text>
        </>
      )}
    </Pressable>
  )
}

export function RiskBadge({ risk, prefix = '' }: { risk: Risk; prefix?: string }) {
  const { colors } = useTheme()
  const r = RISK_STYLE[risk]
  const color = colors[r.color]
  return (
    <View
      style={[styles.badge, { backgroundColor: color + '26', borderColor: color }]}
      accessibilityLabel={`${prefix}${r.label}`}
    >
      <Ionicons name={r.icon} size={14} color={color} />
      <Text style={[styles.badgeText, { color }]}>
        {prefix}
        {r.label}
      </Text>
    </View>
  )
}

export function Chip({ text, tone = 'muted' }: { text: string; tone?: 'accent' | 'muted' }) {
  const { colors, mode } = useTheme()
  const accent = tone === 'accent'
  const accentColor = mode === 'dark' ? colors.accentLight : colors.accent
  return (
    <View
      style={[
        styles.chip,
        accent
          ? {
              backgroundColor: accentColor + '1A',
              borderColor: accentColor,
            }
          : { backgroundColor: colors.bg, borderColor: colors.border },
      ]}
    >
      <Text
        style={{
          color: accent ? accentColor : colors.text,
          fontSize: 13,
          fontWeight: '600',
        }}
      >
        {text}
      </Text>
    </View>
  )
}

export function Banner({
  tone,
  title,
  text,
}: {
  tone: 'critical' | 'warning'
  title: string
  text?: string
}) {
  const { colors } = useTheme()
  const color = tone === 'critical' ? colors.critical : colors.warning
  const icon: IconName = tone === 'critical' ? 'ban' : 'warning'
  return (
    <View style={[styles.banner, { borderColor: color, backgroundColor: color + '1F' }]}>
      <Ionicons name={icon} size={24} color={color} />
      <View style={{ flex: 1, gap: 4 }}>
        <Text style={[styles.bannerTitle, { color }]}>{title}</Text>
        {text ? <Text style={[styles.bannerText, { color: colors.text }]}>{text}</Text> : null}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radius.card,
    padding: 16,
    gap: 10,
    borderWidth: 1,
  },
  section: { fontSize: 17, fontWeight: '700' },
  button: {
    minHeight: 52,
    borderRadius: radius.button,
    paddingHorizontal: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  buttonText: { fontSize: 16, fontWeight: '700' },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  badgeText: { fontSize: 13, fontWeight: '700' },
  chip: { borderWidth: 1, borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 6 },
  banner: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'flex-start',
    borderWidth: 1.5,
    borderRadius: radius.card,
    padding: 14,
  },
  bannerTitle: { fontSize: 16, fontWeight: '800' },
  bannerText: { fontSize: 14, lineHeight: 20 },
})
