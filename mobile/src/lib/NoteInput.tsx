import { Alert, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useDictation } from './speech'
import { colors } from './theme'
import { Card, SectionTitle } from './ui'

const MAX_NOTE = 500

export function NoteInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const dictation = useDictation((text) => {
    onChange(((value ? value.trimEnd() + ' ' : '') + text).slice(0, MAX_NOTE))
  })

  function toggleMic() {
    if (!dictation.supported) {
      Alert.alert(
        "Voice input isn't available here",
        'It works in the installed FixLens app build, not inside Expo Go. For now, use the microphone on your keyboard.',
      )
      return
    }
    if (dictation.listening) dictation.stop()
    else dictation.start()
  }

  return (
    <Card>
      <SectionTitle>Describe the problem (optional)</SectionTitle>
      <View>
        <TextInput
          value={value}
          onChangeText={onChange}
          multiline
          maxLength={MAX_NOTE}
          placeholder="e.g. It clicks but won't heat. Started after I descaled it."
          placeholderTextColor={colors.textMuted}
          style={s.input}
          accessibilityLabel='Describe the problem'
        />
        <Pressable
          onPress={toggleMic}
          accessibilityRole='button'
          accessibilityLabel={dictation.listening ? 'Stop voice input' : 'Start voice input'}
          style={[s.mic, dictation.listening && s.micOn]}
        >
          <Ionicons
            name={dictation.listening ? 'stop' : 'mic'}
            size={22}
            color={dictation.listening ? '#FFFFFF' : colors.onAccent}
          />
        </Pressable>
      </View>
      {dictation.listening ? <Text style={s.listening}>Listening… {dictation.partial}</Text> : null}
      {dictation.error ? <Text style={s.error}>{dictation.error}</Text> : null}
      <Text style={s.hint}>
        Sound isn't analyzed from photos or videos, so describe it here (grinding, clicking,
        humming), along with any burning smell, sparks or shocks. Tap the mic to dictate.
      </Text>
    </Card>
  )
}

const s = StyleSheet.create({
  input: {
    minHeight: 100,
    textAlignVertical: 'top',
    color: colors.text,
    fontSize: 15,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 12,
    paddingRight: 64,
  },
  mic: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  micOn: { backgroundColor: colors.critical },
  listening: { color: colors.accentLight, fontSize: 14 },
  error: { color: colors.warning, fontSize: 14 },
  hint: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
})
