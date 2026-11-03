import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { useTheme, type ThemeColors } from './theme'
import type { HistoryItem } from './storage'
import { formatDate, worstRisk } from './util'
import { Card, RiskBadge } from './ui'

export function HistoryRow({ item }: { item: HistoryItem }) {
  const router = useRouter()
  const { colors } = useTheme()
  const s = makeStyles(colors)
  const d = item.diagnosis
  const worst = worstRisk(d.plan)
  const top = d.hypotheses[0]
  return (
    <Pressable
      accessibilityRole='button'
      onPress={() => router.push({ pathname: '/report/[id]', params: { id: d.id } })}
    >
      <Card>
        <View style={s.row}>
          <Text style={s.title}>{d.appliance ?? 'Not recognised'}</Text>
          {worst ? <RiskBadge risk={worst} /> : null}
        </View>
        <Text style={s.muted}>{formatDate(item.savedAt)}</Text>
        {top ? (
          <Text style={s.body} numberOfLines={1}>
            {top.label === 'most_likely' ? 'Most likely' : 'Possible'}: {top.name}
          </Text>
        ) : null}
      </Card>
    </Pressable>
  )
}

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
    row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
    title: { color: colors.text, fontSize: 17, fontWeight: '700', flexShrink: 1 },
    muted: { color: colors.textMuted, fontSize: 13 },
    body: { color: colors.text, fontSize: 14 },
  })
}
