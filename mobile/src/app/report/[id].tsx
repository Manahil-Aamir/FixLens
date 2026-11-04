import { useEffect, useState } from 'react'
import { ActivityIndicator, Image, StyleSheet, Text, View } from 'react-native'
import { Stack, useLocalSearchParams } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { ResultView } from '../../lib/ResultView'
import { getHistoryItem, type HistoryItem } from '../../lib/storage'
import { radius, useTheme, type ThemeColors } from '../../lib/theme'
import { Card, Screen, SectionTitle } from '../../lib/ui'
import { formatDate } from '../../lib/util'

export default function Report() {
  const { colors } = useTheme()
  const s = makeStyles(colors)
  const { id } = useLocalSearchParams<{ id: string }>()
  const [item, setItem] = useState<HistoryItem | null | undefined>(undefined)
  const [imageBroken, setImageBroken] = useState(false)

  useEffect(() => {
    getHistoryItem(String(id)).then(setItem)
  }, [id])

  return (
    <Screen safeTop={false}>
      <Stack.Screen options={{ title: item?.diagnosis.appliance ?? 'Report' }} />

      {item === undefined ? <ActivityIndicator color={colors.accent} /> : null}

      {item === null ? (
        <Card>
          <Text style={s.body}>This report is no longer available on this phone.</Text>
        </Card>
      ) : null}

      {item ? (
        <>
          <Card>
            <SectionTitle>What you submitted</SectionTitle>
            <Text style={s.muted}>{formatDate(item.savedAt)}</Text>
            {item.mediaKind === 'image' && item.mediaUri && !imageBroken ? (
              <Image
                source={{ uri: item.mediaUri }}
                style={s.photo}
                onError={() => setImageBroken(true)}
                accessibilityLabel='Submitted photo'
              />
            ) : null}
            {item.mediaKind === 'video' ? (
              <View style={s.videoRow}>
                <Ionicons name='videocam' size={22} color={colors.accent} />
                <Text style={s.body}>Video clip</Text>
              </View>
            ) : null}
          </Card>

          {item.qa && item.qa.length > 0 ? (
            <Card>
              <SectionTitle>Your answers</SectionTitle>
              {item.qa.map((x, i) => (
                <View key={i} style={{ gap: 2 }}>
                  <Text style={s.muted}>{x.question}</Text>
                  <Text style={s.answer}>{x.answer}</Text>
                </View>
              ))}
            </Card>
          ) : null}

          <ResultView diagnosis={item.diagnosis} />
        </>
      ) : null}
    </Screen>
  )
}

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
    body: { color: colors.text, fontSize: 15 },
    muted: { color: colors.textMuted, fontSize: 14, lineHeight: 20 },
    answer: { color: colors.text, fontSize: 15, fontWeight: '600' },
    photo: { width: '100%', height: 220, borderRadius: radius.card, backgroundColor: colors.bg },
    videoRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  })
}
