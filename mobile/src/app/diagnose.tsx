import { useEffect, useRef, useState } from 'react'
import { ActivityIndicator, Alert, Image, Pressable, StyleSheet, Text, View } from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import { Ionicons } from '@expo/vector-icons'
import { ApiError, createDiagnosis, sendAnswers } from '../lib/api'
import { ResultView } from '../lib/ResultView'
import { saveToHistory } from '../lib/storage'
import { colors, radius } from '../lib/theme'
import type { Diagnosis } from '../lib/types'
import { Banner, Button, Card, Screen, SectionTitle } from '../lib/ui'

type Phase = 'idle' | 'analyzing' | 'questions' | 'done' | 'error'

export default function DiagnoseScreen() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [photoUri, setPhotoUri] = useState<string | null>(null)
  const [photoMime, setPhotoMime] = useState<string | null>(null)
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const retryRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (phase !== 'analyzing') return
    setElapsed(0)
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [phase])

  async function pick(source: 'camera' | 'library') {
    try {
      let result: ImagePicker.ImagePickerResult
      if (source === 'camera') {
        const perm = await ImagePicker.requestCameraPermissionsAsync()
        if (!perm.granted) {
          Alert.alert(
            'Camera permission needed',
            "Allow camera access in your phone's settings, or choose a photo from the gallery.",
          )
          return
        }
        result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.6 })
      } else {
        result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.6 })
      }
      if (result.canceled || !result.assets?.length) return
      setPhotoUri(result.assets[0].uri)
      setPhotoMime(result.assets[0].mimeType ?? 'image/jpeg')
    } catch {
      Alert.alert("Couldn't open the photo picker", 'Please try again.')
    }
  }

  async function handle(d: Diagnosis) {
    setDiagnosis(d)
    if (d.status === 'needs_answers') {
      setDraft({})
      setPhase('questions')
    } else {
      await saveToHistory(d)
      setPhase('done')
    }
  }

  async function run(action: () => Promise<Diagnosis>) {
    setPhase('analyzing')
    try {
      await handle(await action())
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Something went wrong.')
      retryRef.current = () => run(action)
      setPhase('error')
    }
  }

  function analyze() {
    if (!photoUri) return
    run(() => createDiagnosis(photoUri, photoMime))
  }

  function submit() {
    if (!diagnosis) return
    const answers = diagnosis.questions.map((q) => ({ question_id: q.id, value: draft[q.id] }))
    run(() => sendAnswers(diagnosis.id, answers))
  }

  function reset() {
    setPhase('idle')
    setPhotoUri(null)
    setPhotoMime(null)
    setDiagnosis(null)
    setDraft({})
    setError('')
  }

  if (phase === 'analyzing') {
    return (
      <Screen>
        <Card style={{ alignItems: 'center', gap: 14, paddingVertical: 36 }}>
          <ActivityIndicator size='large' color={colors.accent} />
          <Text style={s.h2}>{diagnosis ? 'Updating your diagnosis' : 'Analyzing your photo'}</Text>
          <Text style={s.muted}>Usually 5–20 seconds · {elapsed}s</Text>
          {elapsed > 30 ? (
            <Text style={s.muted}>Taking longer than usual. Still working…</Text>
          ) : null}
        </Card>
      </Screen>
    )
  }

  if (phase === 'error') {
    return (
      <Screen>
        <Banner tone='critical' title='Something went wrong' text={error} />
        <Button title='Try again' icon='refresh' onPress={() => retryRef.current?.()} />
        <Button title='Start over' variant='secondary' onPress={reset} />
      </Screen>
    )
  }

  if (phase === 'questions' && diagnosis) {
    const ready = diagnosis.questions.every((q) => draft[q.id])
    return (
      <Screen>
        <Text style={s.h1}>A few quick questions</Text>
        <Text style={s.muted}>
          {diagnosis.appliance ? `Detected: ${diagnosis.appliance}. ` : ''}
          Your answers help narrow down the cause.
        </Text>
        {diagnosis.questions.map((q) => (
          <Card key={q.id}>
            <Text style={s.q}>{q.text}</Text>
            {q.options.map((opt) => {
              const selected = draft[q.id] === opt
              return (
                <Pressable
                  key={opt}
                  onPress={() => setDraft((d) => ({ ...d, [q.id]: opt }))}
                  accessibilityRole='radio'
                  accessibilityState={{ selected }}
                  style={[s.option, selected && s.optionSelected]}
                >
                  <Ionicons
                    name={selected ? 'radio-button-on' : 'radio-button-off'}
                    size={22}
                    color={selected ? colors.accent : colors.textMuted}
                  />
                  <Text style={s.optionText}>{opt}</Text>
                </Pressable>
              )
            })}
          </Card>
        ))}
        <Button title='Continue' icon='arrow-forward' disabled={!ready} onPress={submit} />
      </Screen>
    )
  }

  if (phase === 'done' && diagnosis) {
    return (
      <Screen>
        <Text style={s.h1}>Diagnosis</Text>
        <ResultView diagnosis={diagnosis} />
        <Button title='New diagnosis' icon='add' variant='secondary' onPress={reset} />
      </Screen>
    )
  }

  return (
    <Screen>
      <Text style={s.h1}>New diagnosis</Text>
      <Text style={s.muted}>
        Photograph the appliance, ideally showing the damaged or faulty part.
      </Text>

      {photoUri ? (
        <Image source={{ uri: photoUri }} style={s.preview} accessibilityLabel='Selected photo' />
      ) : (
        <Card style={s.placeholder}>
          <Ionicons name='camera-outline' size={44} color={colors.textMuted} />
          <Text style={s.muted}>No photo yet</Text>
        </Card>
      )}

      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{ flex: 1 }}>
          <Button
            title='Camera'
            icon='camera'
            variant={photoUri ? 'secondary' : 'primary'}
            onPress={() => pick('camera')}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Button
            title='Gallery'
            icon='images'
            variant='secondary'
            onPress={() => pick('library')}
          />
        </View>
      </View>

      {photoUri ? <Button title='Analyze' icon='sparkles' onPress={analyze} /> : null}

      <Card>
        <SectionTitle>Tips for a good photo</SectionTitle>
        <Text style={s.muted}>• Good light, no glare</Text>
        <Text style={s.muted}>• One appliance in the frame</Text>
        <Text style={s.muted}>• Get close to the problem area</Text>
      </Card>
    </Screen>
  )
}

const s = StyleSheet.create({
  h1: { color: colors.text, fontSize: 26, fontWeight: '800' },
  h2: { color: colors.text, fontSize: 19, fontWeight: '700' },
  muted: { color: colors.textMuted, fontSize: 15, lineHeight: 22 },
  q: { color: colors.text, fontSize: 16, fontWeight: '700', lineHeight: 22 },
  preview: {
    width: '100%',
    height: 260,
    borderRadius: radius.card,
    backgroundColor: colors.surface,
  },
  placeholder: { height: 200, alignItems: 'center', justifyContent: 'center' },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 12,
    minHeight: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  optionSelected: { borderColor: colors.accent, backgroundColor: colors.accent + '1A' },
  optionText: { color: colors.text, fontSize: 15, flex: 1 },
})
