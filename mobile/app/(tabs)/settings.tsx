import { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, ActivityIndicator, ScrollView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAppStore } from '../../stores/appStore';
import * as WebBrowser from 'expo-web-browser';
import { api } from '../../lib/api';

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
  success: '#8B9A6F',
  successLight: '#EDF2E7',
  error: '#B87060',
  google: '#EA4335',
  googleLight: '#FEE8E6',
  microsoft: '#0078D4',
  microsoftLight: '#E6F1FC',
};

export default function SettingsScreen() {
  const { user, logout, refreshUser } = useAppStore();
  const [connectingGoogle, setConnectingGoogle] = useState(false);
  const [connectingMicrosoft, setConnectingMicrosoft] = useState(false);
  const [connectingSlack, setConnectingSlack] = useState(false);

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: logout },
    ]);
  };

  const handleConnectGoogle = async () => {
    if (user?.googleConnected) {
      Alert.alert('Already Connected', 'Your Google account is already connected.');
      return;
    }

    setConnectingGoogle(true);
    try {
      const response = await api.get('/auth/google/connect');
      const authUrl = response.auth_url;

      if (!authUrl) {
        throw new Error('Google OAuth is not configured');
      }

      await WebBrowser.openBrowserAsync(authUrl);
      await refreshUser();
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to connect Google');
    } finally {
      setConnectingGoogle(false);
    }
  };

  const handleConnectMicrosoft = async () => {
    if (user?.microsoftConnected) {
      Alert.alert('Already Connected', 'Your Microsoft account is already connected.');
      return;
    }

    setConnectingMicrosoft(true);
    try {
      const response = await api.get('/auth/microsoft/connect');
      const authUrl = response.auth_url;

      if (!authUrl) {
        throw new Error('Microsoft OAuth is not configured');
      }

      await WebBrowser.openBrowserAsync(authUrl);
      await refreshUser();
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to connect Microsoft');
    } finally {
      setConnectingMicrosoft(false);
    }
  };

  const handleConnectSlack = async () => {
    if (user?.slackConnected) {
      Alert.alert('Already Connected', 'Your Slack workspace is already connected.');
      return;
    }

    setConnectingSlack(true);
    try {
      const response = await api.get('/auth/slack/connect');
      const authUrl = response.auth_url;

      if (!authUrl) {
        throw new Error('Slack OAuth is not configured');
      }

      await WebBrowser.openBrowserAsync(authUrl);
      await refreshUser();
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to connect Slack');
    } finally {
      setConnectingSlack(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Profile Card */}
      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarEmoji}>☕</Text>
        </View>
        <Text style={styles.userEmail}>{user?.email}</Text>
        <View style={styles.statusBadge}>
          <View style={styles.statusDot} />
          <Text style={styles.statusText}>Signed in</Text>
        </View>
      </View>

      {/* Connected Accounts */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connected Accounts</Text>
        
        <TouchableOpacity 
          style={styles.connectionCard}
          onPress={handleConnectGoogle}
          disabled={connectingGoogle}
        >
          <View style={[styles.connectionIcon, { backgroundColor: colors.googleLight }]}>
            <Ionicons name="logo-google" size={22} color={colors.google} />
          </View>
          <View style={styles.connectionInfo}>
            <Text style={styles.connectionName}>Google</Text>
            <Text style={styles.connectionStatus}>
              {user?.googleConnected ? 'Calendar & Gmail connected' : 'Tap to connect'}
            </Text>
          </View>
          {connectingGoogle ? (
            <ActivityIndicator color={colors.google} />
          ) : user?.googleConnected ? (
            <Ionicons name="checkmark-circle" size={24} color={colors.success} />
          ) : (
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          )}
        </TouchableOpacity>

        <TouchableOpacity 
          style={styles.connectionCard}
          onPress={handleConnectMicrosoft}
          disabled={connectingMicrosoft}
        >
          <View style={[styles.connectionIcon, { backgroundColor: colors.microsoftLight }]}>
            <Ionicons name="logo-microsoft" size={22} color={colors.microsoft} />
          </View>
          <View style={styles.connectionInfo}>
            <Text style={styles.connectionName}>Microsoft</Text>
            <Text style={styles.connectionStatus}>
              {user?.microsoftConnected ? 'Outlook connected' : 'Tap to connect'}
            </Text>
          </View>
          {connectingMicrosoft ? (
            <ActivityIndicator color={colors.microsoft} />
          ) : user?.microsoftConnected ? (
            <Ionicons name="checkmark-circle" size={24} color={colors.success} />
          ) : (
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          )}
        </TouchableOpacity>

        <TouchableOpacity 
          style={styles.connectionCard}
          onPress={handleConnectSlack}
          disabled={connectingSlack}
        >
          <View style={[styles.connectionIcon, { backgroundColor: '#F4E5F7' }]}>
            <Ionicons name="chatbubbles" size={22} color="#4A154B" />
          </View>
          <View style={styles.connectionInfo}>
            <Text style={styles.connectionName}>Slack</Text>
            <Text style={styles.connectionStatus}>
              {user?.slackConnected ? 'Workspace connected' : 'Tap to connect'}
            </Text>
          </View>
          {connectingSlack ? (
            <ActivityIndicator color="#4A154B" />
          ) : user?.slackConnected ? (
            <Ionicons name="checkmark-circle" size={24} color={colors.success} />
          ) : (
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          )}
        </TouchableOpacity>
      </View>

      {/* About */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.aboutCard}>
          <Text style={styles.aboutEmoji}>☕</Text>
          <Text style={styles.appName}>Donna</Text>
          <Text style={styles.appVersion}>Version 1.0.0</Text>
          <Text style={styles.appTagline}>Your personal assistant</Text>
        </View>
      </View>

      {/* Sign Out */}
      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Ionicons name="log-out-outline" size={20} color={colors.error} />
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>

      <View style={styles.bottomPadding} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: 20,
  },
  profileCard: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    marginBottom: 24,
    borderWidth: 1,
    borderColor: colors.border,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarEmoji: {
    fontSize: 36,
  },
  userEmail: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.successLight,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.success,
  },
  statusText: {
    color: colors.success,
    fontSize: 13,
    fontWeight: '500',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 12,
    marginLeft: 4,
  },
  connectionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  connectionIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  connectionInfo: {
    flex: 1,
  },
  connectionName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  connectionStatus: {
    fontSize: 13,
    color: colors.textMuted,
  },
  aboutCard: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 28,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  aboutEmoji: {
    fontSize: 40,
    marginBottom: 12,
  },
  appName: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.text,
    fontFamily: Platform.OS === 'ios' ? 'Georgia' : 'serif',
  },
  appVersion: {
    fontSize: 13,
    color: colors.textMuted,
    marginTop: 4,
  },
  appTagline: {
    fontSize: 14,
    color: colors.textMuted,
    marginTop: 8,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.error,
  },
  bottomPadding: {
    height: 40,
  },
});
