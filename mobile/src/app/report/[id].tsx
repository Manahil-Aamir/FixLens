import { useEffect, useState } from 'react'
import { ActivityIndicator, Text } from 'react-native'
import { useLocalSearchParams } from 'expo-router'
import { ResultView } from '../../lib/ResultView'
import { getHistoryItem, type HistoryItem } from '../../lib/storage'
import { colors } from '../../lib/theme'
import { Card, Screen } from '../../lib/ui'

export default function Report() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const [item, setItem] = useState<HistoryItem | null | undefined>(undefined)

  useEffect(() => {
    getHistoryItem(String(id)).then(setItem)
  }, [id])

  return (
    <Screen safeTop={false}>
      {item === undefined ? <ActivityIndicator color={colors.accent} /> : null}
      {item === null ? (
        <Card>
          <Text style={{ color: colors.text }}>
            This report is no longer available on this phone.
          </Text>
        </Card>
      ) : null}
      {item ? <ResultView diagnosis={item.diagnosis} /> : null}
    </Screen>
  )
}
