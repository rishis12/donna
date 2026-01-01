import { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAppStore } from '../stores/appStore';
import { Ionicons } from '@expo/vector-icons';
import * as WebBrowser from 'expo-web-browser';
import { api } from '../lib/api';

WebBrowser.maybeCompleteAuthSession();

// Earthy tan/brown colors
const colors = {
  background: '#FAF8F5',
  surface: '#FFFFFF',
  surfaceAlt: '#F5F0E8',
  primary: '#B89460',
  primaryLight: '#F7F3EE',
  text: '#443D35',
  textMuted: '#9C8B78',
  border: '#E8DFD3',
  error: '#B87060',
  success: '#8B9B6A',
  google: '#EA4335',
  slack: '#4A154B',
};

interface ConnectionItem {
  id: 'google' | 'slack' | 'email';
  title: string;
  description: string;
  icon: string;
  connected: boolean;
}

export default function OnboardingScreen() {
  const router = useRouter();
  const { user, refreshUser, completeOnboarding } = useAppStore();
  const [isConnecting, setIsConnecting] = useState<'google' | 'slack' | null>(null);
  const [error, setError] = useState('');

  const googleConnected = user?.googleConnected || false;
  const slackConnected = user?.slackConnected || false;
  const emailConnected = user?.googleConnected || user?.microsoftConnected || false;

  const connections: ConnectionItem[] = [
    {
      id: 'google',
      title: 'Connect Google',
      description: 'Calendar and Gmail',
      icon: 'logo-google',
      connected: googleConnected,
    },
    {
      id: 'slack',
      title: 'Connect Slack',
      description: 'Team communication',
      icon: 'logo-slack',
      connected: slackConnected,
    },
    {
      id: 'email',
      title: 'Connect Email',
      description: 'Gmail or Outlook',
      icon: 'mail',
      connected: emailConnected,
    },
  ];

  const handleConnect = async (provider: 'google' | 'slack') => {
    setError('');
    setIsConnecting(provider);

    try {
      const response = await api.get(`/auth/${provider}/connect`);
      const authUrl = response.auth_url;

      if (!authUrl) {
        throw new Error(`${provider} connection is not configured`);
      }

      await WebBrowser.openBrowserAsync(authUrl);
      
      // Refresh user after a short delay
      setTimeout(async () => {
        await refreshUser();
        setIsConnecting(null);
      }, 2000);
    } catch (err: any) {
      setError(err.message || `Failed to connect ${provider}`);
      setIsConnecting(null);
    }
  };

  const handleContinue = async () => {
    try {
      await completeOnboarding();
      router.replace('/(tabs)');
    } catch (err: any) {
      setError('Failed to complete onboarding');
    }
  };

  const allConnected = googleConnected && slackConnected && emailConnected;

  return (
    <ScrollView 
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.inner}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logo}>
            <Text style={styles.logoEmoji}>👋</Text>
          </View>
          <Text style={styles.title}>Welcome to Donna</Text>
          <Text style={styles.subtitle}>Let's connect your services to get started</Text>
        </View>

        {/* Connection Items */}
        <View style={styles.connections}>
          {connections.map((connection) => (
            <View
              key={connection.id}
              style={[
                styles.connectionItem,
                connection.connected && styles.connectionItemConnected,
              ]}
            >
              <View style={styles.connectionLeft}>
                <View
                  style={[
                    styles.iconContainer,
                    connection.connected && styles.iconContainerConnected,
                  ]}
                >
                  {connection.connected ? (
                    <Ionicons name="checkmark" size={20} color="#FFFFFF" />
                  ) : (
                    <Ionicons
                      name={connection.icon as any}
                      size={20}
                      color={connection.connected ? '#FFFFFF' : colors.textMuted}
                    />
                  )}
                </View>
                <View style={styles.connectionText}>
                  <Text style={styles.connectionTitle}>{connection.title}</Text>
                  <Text style={styles.connectionDescription}>{connection.description}</Text>
                </View>
              </View>
              {!connection.connected && connection.id !== 'email' && (
                <TouchableOpacity
                  style={styles.connectButton}
                  onPress={() => handleConnect(connection.id)}
                  disabled={isConnecting !== null}
                >
                  {isConnecting === connection.id ? (
                    <ActivityIndicator color="#FFFFFF" size="small" />
                  ) : (
                    <Text style={styles.connectButtonText}>Connect</Text>
                  )}
                </TouchableOpacity>
              )}
              {connection.connected && connection.id === 'email' && (
                <Text style={styles.connectedText}>
                  Connected via {user?.googleConnected ? 'Google' : 'Microsoft'}
                </Text>
              )}
            </View>
          ))}
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        {/* Continue Button */}
        <TouchableOpacity
          style={[styles.continueButton, !allConnected && styles.continueButtonDisabled]}
          onPress={handleContinue}
          disabled={!allConnected}
        >
          <Text style={styles.continueButtonText}>Continue</Text>
        </TouchableOpacity>

        <Text style={styles.footerText}>
          You can connect additional services later in Settings
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    flexGrow: 1,
  },
  inner: {
    flex: 1,
    padding: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
    marginTop: 20,
  },
  logo: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  logoEmoji: {
    fontSize: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.text,
    marginBottom: 8,
    fontFamily: Platform.OS === 'ios' ? 'Georgia' : 'serif',
  },
  subtitle: {
    fontSize: 16,
    color: colors.textMuted,
    textAlign: 'center',
  },
  connections: {
    gap: 14,
    marginBottom: 24,
  },
  connectionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderRadius: 14,
    backgroundColor: colors.surface,
    borderWidth: 2,
    borderColor: colors.border,
  },
  connectionItemConnected: {
    backgroundColor: '#F0F9F4',
    borderColor: colors.success,
  },
  connectionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: 12,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.surfaceAlt,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconContainerConnected: {
    backgroundColor: colors.success,
  },
  connectionText: {
    flex: 1,
  },
  connectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  connectionDescription: {
    fontSize: 14,
    color: colors.textMuted,
  },
  connectButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 12,
    backgroundColor: colors.primary,
  },
  connectButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  connectedText: {
    fontSize: 14,
    color: colors.success,
    fontWeight: '600',
  },
  error: {
    color: colors.error,
    textAlign: 'center',
    fontSize: 14,
    marginBottom: 16,
  },
  continueButton: {
    backgroundColor: colors.primary,
    borderRadius: 14,
    padding: 16,
    alignItems: 'center',
    marginBottom: 16,
  },
  continueButtonDisabled: {
    backgroundColor: colors.border,
    opacity: 0.6,
  },
  continueButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  footerText: {
    color: colors.textMuted,
    textAlign: 'center',
    fontSize: 12,
  },
});
