import { useState } from 'react'
import { Image, Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import type { HistoryItem } from './storage'
import { useTheme, type ThemeColors } from './theme'
import { Card, RiskBadge } from './ui'
import { formatDate, worstRisk } from './util'

export function HistoryRow({ item, onPress }: { item: HistoryItem; onPress?: () => void }) {
  const router = useRouter()
  const { colors } = useTheme()
  const s = makeStyles(colors)
  const [broken, setBroken] = useState(false)
  const d = item.diagnosis
  const worst = worstRisk(d.plan)
  const top = d.hypotheses[0]
  const showImage = item.mediaKind === 'image' && !!item.mediaUri && !broken

  return (
    <Pressable
      accessibilityRole='button'
      onPress={onPress ?? (() => router.push({ pathname: '/report/[id]', params: { id: d.id } }))}
    >
      <Card>
        <View style={s.row}>
          {showImage ? (
            <Image
              source={{ uri: item.mediaUri as string }}
              style={s.thumb}
              onError={() => setBroken(true)}
            />
          ) : item.mediaKind === 'video' ? (
            <View style={[s.thumb, s.thumbIcon]}>
              <Ionicons name='videocam' size={22} color={colors.accent} />
            </View>
          ) : null}
          <View style={{ flex: 1, gap: 4 }}>
            <View style={s.titleRow}>
              <Text style={s.title}>{d.appliance ?? 'Not recognised'}</Text>
              {worst ? <RiskBadge risk={worst} /> : null}
            </View>
            <Text style={s.muted}>{formatDate(item.savedAt)}</Text>
            {top ? (
              <Text style={s.body} numberOfLines={1}>
                {top.label === 'most_likely' ? 'Most likely' : 'Possible'}: {top.name}
              </Text>
            ) : null}
          </View>
          <Ionicons name='chevron-forward' size={20} color={colors.textMuted} />
        </View>
      </Card>
    </Pressable>
  )
}

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
    row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
    titleRow: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 8,
    },
    thumb: { width: 56, height: 56, borderRadius: 10, backgroundColor: colors.bg },
    thumbIcon: { alignItems: 'center', justifyContent: 'center' },
    title: { color: colors.text, fontSize: 17, fontWeight: '700', flexShrink: 1 },
    muted: { color: colors.textMuted, fontSize: 13 },
    body: { color: colors.text, fontSize: 14 },
  })
}
