import { useCallback, useEffect, useRef, useState } from 'react'

type SpeechLib = typeof import('expo-speech-recognition')

// Expo Go doesn't contain the native module, so load it defensively.
let speech: SpeechLib | null = null
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const m = require('expo-speech-recognition')
  speech = m?.ExpoSpeechRecognitionModule ? m : null
} catch {
  speech = null
}

export const dictationSupported = speech !== null

export function useDictation(onFinalText: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const [partial, setPartial] = useState('')
  const [error, setError] = useState<string | null>(null)
  const callback = useRef(onFinalText)
  callback.current = onFinalText

  useEffect(() => {
    if (!speech) return
    const M = speech.ExpoSpeechRecognitionModule
    const subs = [
      M.addListener('start', () => {
        setListening(true)
        setError(null)
      }),
      M.addListener('end', () => {
        setListening(false)
        setPartial('')
      }),
      M.addListener('result', (e: any) => {
        const text: string = e?.results?.[0]?.transcript ?? ''
        if (e?.isFinal) {
          if (text.trim()) callback.current(text.trim())
          setPartial('')
        } else {
          setPartial(text)
        }
      }),
      M.addListener('error', (e: any) => {
        setListening(false)
        setPartial('')
        if (e?.error !== 'aborted' && e?.error !== 'no-speech') {
          setError(e?.message || 'Voice input failed. Please try again.')
        }
      }),
    ]
    return () => subs.forEach((s) => s.remove())
  }, [])

  const start = useCallback(async () => {
    if (!speech) return
    const M = speech.ExpoSpeechRecognitionModule
    try {
      if (typeof M.isRecognitionAvailable === 'function' && !M.isRecognitionAvailable()) {
        setError("Voice input isn't available on this phone.")
        return
      }
      const perm = await M.requestPermissionsAsync()
      if (!perm.granted) {
        setError("Allow microphone access in your phone's settings to use voice input.")
        return
      }
      M.start({ lang: 'en-US', interimResults: true, continuous: false })
    } catch {
      setError("Couldn't start voice input.")
    }
  }, [])

  const stop = useCallback(() => {
    speech?.ExpoSpeechRecognitionModule.stop()
  }, [])

  return { supported: dictationSupported, listening, partial, error, start, stop }
}
