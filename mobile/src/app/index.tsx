import { useCallback, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useFocusEffect, useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { API_URL, listObjects } from '../lib/api'
import { HistoryRow } from '../lib/HistoryRow'
import { loadHistory, type HistoryItem } from '../lib/storage'
import { useTheme, type ThemeColors } from '../lib/theme'
import type { Supported } from '../lib/types'
import { Banner, Button, Card, Chip, Screen, SectionTitle } from '../lib/ui'

export default function Home() {
  const router = useRouter()
  const { colors, mode, toggleTheme } = useTheme()
  const s = makeStyles(colors)
  const [objects, setObjects] = useState<Supported[] | null>(null)
  const [offline, setOffline] = useState(false)
  const [recent, setRecent] = useState<HistoryItem[]>([])

  useFocusEffect(
    useCallback(() => {
      let active = true
      loadHistory().then((h) => active && setRecent(h.slice(0, 3)))
      listObjects()
        .then((o) => {
          if (!active) return
          setObjects(o)
          setOffline(false)
        })
        .catch(() => active && setOffline(true))
      return () => {
        active = false
      }
    }, []),
  )

  return (
    <Screen>
      <View style={s.header}>
        <View style={s.brand}>
          <Ionicons name='scan-circle' size={32} color={colors.accent} />
          <Text style={s.brandText}>FixLens</Text>
        </View>
        <Pressable
          accessibilityRole='button'
          accessibilityLabel={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}
          onPress={toggleTheme}
          style={({ pressed }) => [s.themeToggle, pressed && { opacity: 0.75 }]}
        >
          <Ionicons
            name={mode === 'dark' ? 'sunny-outline' : 'moon-outline'}
            size={18}
            color={colors.accent}
          />
          <Text style={s.toggleText}>{mode === 'dark' ? 'Light' : 'Dark'}</Text>
        </Pressable>
      </View>

      <Card style={{ gap: 12 }}>
        <Text style={s.h1}>What's broken?</Text>
        <Text style={s.muted}>
          Take a photo of your appliance. FixLens spots the likely fault and gives you a safe,
          step-by-step plan.
        </Text>
        <Button title='Start diagnosis' icon='camera' onPress={() => router.push('/diagnose')} />
      </Card>

      {offline ? (
        <Banner
          tone='warning'
          title="Can't reach the server"
          text={`Tried ${API_URL}. Check that the backend is running and your phone is on the same Wi-Fi.`}
        />
      ) : null}

      {objects ? (
        <Card>
          <SectionTitle>Supported appliances</SectionTitle>
          <View style={s.wrap}>
            {objects.map((o) => (
              <Chip key={o.id} text={o.name} />
            ))}
          </View>
        </Card>
      ) : null}

      {recent.length > 0 ? (
        <View style={{ gap: 12 }}>
          <SectionTitle>Recent diagnoses</SectionTitle>
          {recent.map((item) => (
            <HistoryRow key={item.diagnosis.id} item={item} />
          ))}
        </View>
      ) : null}
    </Screen>
  )
}

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
    header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
    brand: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    brandText: { color: colors.text, fontSize: 22, fontWeight: '800' },
    themeToggle: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 6,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 999,
      paddingHorizontal: 12,
      paddingVertical: 8,
    },
    toggleText: { color: colors.accent, fontSize: 14, fontWeight: '700' },
    h1: { color: colors.text, fontSize: 24, fontWeight: '800' },
    muted: { color: colors.textMuted, fontSize: 15, lineHeight: 22 },
    wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  })
}
