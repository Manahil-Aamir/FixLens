import { Stack } from 'expo-router'
import { ThemeProvider, useTheme } from '../lib/theme'

export default function RootLayout() {
  return (
    <ThemeProvider>
      <AppStack />
    </ThemeProvider>
  )
}

function AppStack() {
  const { colors } = useTheme()
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.accent,
        headerTitleStyle: { color: colors.text },
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen name='(tabs)' options={{ headerShown: false }} />
      <Stack.Screen name='report/[id]' options={{ title: 'Past diagnosis' }} />
    </Stack>
  )
}
