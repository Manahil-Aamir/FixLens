import { useCallback, useState } from 'react'
import { Alert, StyleSheet, Text } from 'react-native'
import { useFocusEffect } from 'expo-router'
import { HistoryRow } from '../../lib/HistoryRow'
import { ResultView } from '../../lib/ResultView'
import { clearHistory, loadHistory, type HistoryItem } from '../../lib/storage'
import { useTheme, type ThemeColors } from '../../lib/theme'
import { Button, Card, Screen } from '../../lib/ui'

export default function History() {
  const { colors } = useTheme()
  const s = makeStyles(colors)
  const [items, setItems] = useState<HistoryItem[] | null>(null)
  const [selected, setSelected] = useState<HistoryItem | null>(null)

  useFocusEffect(
    useCallback(() => {
      let active = true
      loadHistory().then((h) => active && setItems(h))
      return () => {
        active = false
      }
    }, []),
  )

  function confirmClear() {
    Alert.alert('Clear history?', 'This removes all saved diagnoses from this phone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Clear',
        style: 'destructive',
        onPress: async () => {
          await clearHistory()
          setItems([])
        },
      },
    ])
  }

  if (selected) {
    return (
      <Screen>
        <Button
          title='Back to history'
          variant='secondary'
          icon='arrow-back'
          onPress={() => setSelected(null)}
        />
        <Text style={s.h1}>Past diagnosis</Text>
        <ResultView diagnosis={selected.diagnosis} />
      </Screen>
    )
  }

  return (
    <Screen>
      <Text style={s.h1}>History</Text>
      {items && items.length === 0 ? (
        <Card>
          <Text style={s.muted}>No diagnoses yet. Your finished diagnoses will appear here.</Text>
        </Card>
      ) : null}
      {items?.map((item) => (
        <HistoryRow
          key={item.diagnosis.id}
          item={item}
          onPress={() => setSelected(item)}
        />
      ))}
      {items && items.length > 0 ? (
        <Button
          title='Clear history'
          variant='secondary'
          icon='trash-outline'
          onPress={confirmClear}
        />
      ) : null}
    </Screen>
  )
}

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
    h1: { color: colors.text, fontSize: 26, fontWeight: '800' },
    muted: { color: colors.textMuted, fontSize: 15, lineHeight: 22 },
  })
}
