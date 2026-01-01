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
  const { init, isAuthenticated, isLoading, user } = useAppStore();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    init();
  }, []);

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(tabs)';
    const onOnboarding = segments[0] === 'onboarding';
    const onLogin = segments[0] === 'login';

    if (!isAuthenticated) {
      if (inAuthGroup || onOnboarding) {
        router.replace('/login');
      }
    } else if (isAuthenticated && user) {
      // Check if onboarding is needed
      if (!user.onboardingComplete) {
        if (inAuthGroup || onLogin) {
          router.replace('/onboarding');
        }
      } else {
        // Onboarding complete, redirect to tabs if needed
        if (onLogin || onOnboarding) {
          router.replace('/(tabs)');
        }
      }
    }
  }, [isAuthenticated, isLoading, segments, user]);

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
        <Stack.Screen name="onboarding" options={{ headerShown: false }} />
      </Stack>
    </>
  );
}
