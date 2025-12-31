import { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View } from 'react-native';
import { useAppStore } from '../stores/appStore';

// Earthy tan/brown colors
const colors = {
  background: '#FAF8F5',
  text: '#443D35',
};

export default function RootLayout() {
  const { init, isAuthenticated, isLoading } = useAppStore();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    init();
  }, []);

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(tabs)';

    if (isAuthenticated && !inAuthGroup) {
      router.replace('/(tabs)');
    } else if (!isAuthenticated && inAuthGroup) {
      router.replace('/login');
    }
  }, [isAuthenticated, isLoading, segments]);

  if (isLoading) {
    return <View style={{ flex: 1, backgroundColor: colors.background }} />;
  }

  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.text,
          headerTitleStyle: { fontWeight: '600', fontFamily: 'Georgia' },
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="login" options={{ headerShown: false }} />
      </Stack>
    </>
  );
}
