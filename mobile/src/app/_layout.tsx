import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { ThemeProvider, useTheme } from '../lib/theme'

export default function TabLayout() {
  return (
    <ThemeProvider>
      <AppTabs />
    </ThemeProvider>
  )
}

function AppTabs() {
  const { colors } = useTheme()
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
      }}
    >
      <Tabs.Screen
        name='index'
        options={{
          title: 'Home',
          tabBarIcon: ({ focused, size }) => (
            <Ionicons
              name='home-outline'
              color={focused ? colors.accent : colors.textMuted}
              size={size}
            />
          ),
        }}
      />
      <Tabs.Screen
        name='diagnose'
        options={{
          title: 'Diagnose',
          tabBarIcon: ({ focused, size }) => (
            <Ionicons
              name='scan-outline'
              color={focused ? colors.accent : colors.textMuted}
              size={size}
            />
          ),
        }}
      />
      <Tabs.Screen
        name='history'
        options={{
          title: 'History',
          tabBarIcon: ({ focused, size }) => (
            <Ionicons
              name='time-outline'
              color={focused ? colors.accent : colors.textMuted}
              size={size}
            />
          ),
        }}
      />
    </Tabs>
  )
}
