import { useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import { Ionicons } from '@expo/vector-icons'
import { ApiError, createDiagnosis, sendAnswers } from '../../lib/api'
import { ResultView } from '../../lib/ResultView'
import { saveToHistory, type QA } from '../../lib/storage'
import { radius, useTheme, type ThemeColors, type ThemeMode } from '../../lib/theme'
import type { Diagnosis } from '../../lib/types'
import { Banner, Button, Card, Screen, SectionTitle } from '../../lib/ui'
import { NoteInput } from '../../lib/NoteInput'

type Phase = 'idle' | 'analyzing' | 'questions' | 'done' | 'error'
type Media = { uri: string; kind: 'image' | 'video'; seconds?: number }

const MAX_VIDEO_SECONDS = 60
const MAX_VIDEO_BYTES = 120 * 1024 * 1024
const MAX_NOTE = 500

export default function DiagnoseScreen() {
  const { colors, mode } = useTheme()
  const s = makeStyles(colors, mode)
  const [phase, setPhase] = useState<Phase>('idle')
  const [media, setMedia] = useState<Media | null>(null)
  const [note, setNote] = useState('')
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const retryRef = useRef<(() => void) | null>(null)
  const qaRef = useRef<QA[]>([])

  useEffect(() => {
    if (phase !== 'analyzing') return
    setElapsed(0)
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [phase])

  async function pick(source: 'photo' | 'video' | 'library') {
    try {
      let result: ImagePicker.ImagePickerResult
      if (source === 'library') {
        result = await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ['images', 'videos'],
          quality: 0.6,
        })
      } else {
        const perm = await ImagePicker.requestCameraPermissionsAsync()
        if (!perm.granted) {
          Alert.alert(
            'Camera permission needed',
            "Allow camera access in your phone's settings, or choose a file from the gallery.",
          )
          return
        }
        result = await ImagePicker.launchCameraAsync(
          source === 'video'
            ? { mediaTypes: ['videos'], videoMaxDuration: MAX_VIDEO_SECONDS }
            : { mediaTypes: ['images'], quality: 0.6 },
        )
      }
      if (result.canceled || !result.assets?.length) return
      const asset = result.assets[0]
      if (asset.type === 'video' && asset.fileSize && asset.fileSize > MAX_VIDEO_BYTES) {
        Alert.alert(
          'Video is too large',
          'The limit is 120 MB. Try a shorter clip, or set your camera to 1080p or 720p.',
        )
        return
      }
      setMedia({
        uri: asset.uri,
        kind: asset.type === 'video' ? 'video' : 'image',
        seconds: asset.duration ? Math.round(asset.duration / 1000) : undefined,
      })
    } catch {
      Alert.alert("Couldn't open the camera or gallery", 'Please try again.')
    }
  }

  async function handle(d: Diagnosis) {
    setDiagnosis(d)
    if (d.status === 'needs_answers') {
      setDraft({})
      setPhase('questions')
    } else {
      await saveToHistory(d, { mediaUri: media?.uri, mediaKind: media?.kind, qa: qaRef.current })
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
    if (!media) return
    run(() => createDiagnosis(media.uri, media.kind, note))
  }

  function submit() {
    if (!diagnosis) return
    const answers = diagnosis.questions.map((q) => ({ question_id: q.id, value: draft[q.id] }))
    qaRef.current = [
      ...qaRef.current,
      ...diagnosis.questions.map((q) => ({ question: q.text, answer: draft[q.id] })),
    ]
    run(() => sendAnswers(diagnosis.id, answers))
  }
  s

  function reset() {
    qaRef.current = []
    setPhase('idle')
    setMedia(null)
    setNote('')
    setDiagnosis(null)
    setDraft({})
    setError('')
  }

  if (phase === 'analyzing') {
    const isVideo = media?.kind === 'video' && !diagnosis
    return (
      <Screen>
        <Card style={{ alignItems: 'center', gap: 14, paddingVertical: 36 }}>
          <ActivityIndicator size='large' color={colors.accent} />
          <Text style={s.h2}>
            {diagnosis
              ? 'Updating your diagnosis'
              : isVideo
                ? 'Analyzing your video'
                : 'Analyzing your photo'}
          </Text>
          <Text style={s.muted}>
            {isVideo ? 'Videos can take up to a minute' : 'Usually 5–30 seconds'} · {elapsed}s
          </Text>
          {elapsed > 60 ? (
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
                    color={
                      selected
                        ? mode === 'dark'
                          ? colors.accentLight
                          : colors.accent
                        : colors.textMuted
                    }
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
        Take a photo, or film the problem for up to a minute, ideally showing the damaged or faulty
        part.
      </Text>

      {media?.kind === 'image' ? (
        <Image source={{ uri: media.uri }} style={s.preview} accessibilityLabel='Selected photo' />
      ) : media?.kind === 'video' ? (
        <Card style={s.placeholder}>
          <Ionicons
            name='videocam'
            size={44}
            color={mode === 'dark' ? colors.accentLight : colors.accent}
          />
          <Text style={s.h2}>Video ready</Text>
          <Text style={s.muted}>
            {media.seconds ? `${media.seconds} s · ` : ''}
            {media.seconds && media.seconds > MAX_VIDEO_SECONDS
              ? 'only the first 60 seconds will be analyzed'
              : 'the whole clip will be analyzed'}
          </Text>
        </Card>
      ) : (
        <Card style={s.placeholder}>
          <Ionicons name='camera-outline' size={44} color={colors.textMuted} />
          <Text style={s.muted}>Nothing selected yet</Text>
        </Card>
      )}

      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{ flex: 1 }}>
          <Button
            title='Photo'
            icon='camera'
            variant={media ? 'secondary' : 'primary'}
            onPress={() => pick('photo')}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Button title='Video' icon='videocam' variant='secondary' onPress={() => pick('video')} />
        </View>
      </View>
      <Button
        title='Choose from gallery'
        icon='images'
        variant='secondary'
        onPress={() => pick('library')}
      />

      <NoteInput value={note} onChange={setNote} />

      {media ? <Button title='Analyze' icon='sparkles' onPress={analyze} /> : null}

      <Card>
        <SectionTitle>Tips</SectionTitle>
        <Text style={s.muted}>• Good light, one appliance in the frame</Text>
        <Text style={s.muted}>• Get close to the problem area</Text>
        <Text style={s.muted}>• Video: film at 1080p or 720p. Very large files are refused.</Text>
      </Card>
    </Screen>
  )
}

function makeStyles(colors: ThemeColors, mode: ThemeMode) {
  return StyleSheet.create({
    h1: { color: colors.text, fontSize: 26, fontWeight: '800' },
    h2: { color: colors.text, fontSize: 19, fontWeight: '700' },
    muted: { color: colors.textMuted, fontSize: 15, lineHeight: 22 },
    hint: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
    q: { color: colors.text, fontSize: 16, fontWeight: '700', lineHeight: 22 },
    preview: {
      width: '100%',
      height: 260,
      borderRadius: radius.card,
      backgroundColor: colors.surface,
    },
    placeholder: { height: 200, alignItems: 'center', justifyContent: 'center' },
    input: {
      minHeight: 90,
      textAlignVertical: 'top',
      color: colors.text,
      fontSize: 15,
      backgroundColor: colors.bg,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 12,
      padding: 12,
    },
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
    optionSelected: {
      borderColor: mode === 'dark' ? colors.accentLight : colors.accent,
      backgroundColor: (mode === 'dark' ? colors.accentLight : colors.accent) + '1A',
    },
    optionText: { color: colors.text, fontSize: 15, flex: 1 },
  })
}
