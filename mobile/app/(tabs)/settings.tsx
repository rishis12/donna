import { View, Text, StyleSheet, TouchableOpacity, Alert, Linking } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAppStore } from '../../stores/appStore';

export default function SettingsScreen() {
  const { user, logout } = useAppStore();

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: logout },
    ]);
  };

  const handleConnectGoogle = () => {
    // For mobile, we'd use OAuth with deep linking
    // For now, show instructions
    Alert.alert(
      'Connect Google',
      'To connect your Google account, please use the desktop app. Your account will sync across devices.',
      [{ text: 'OK' }]
    );
  };

  const handleConnectMicrosoft = () => {
    Alert.alert(
      'Connect Microsoft',
      'To connect your Microsoft account, please use the desktop app. Your account will sync across devices.',
      [{ text: 'OK' }]
    );
  };

  return (
    <View style={styles.container}>
      {/* User Info */}
      <View style={styles.section}>
        <View style={styles.userCard}>
          <View style={styles.avatar}>
            <Ionicons name="person" size={32} color="#f59e0b" />
          </View>
          <View style={styles.userInfo}>
            <Text style={styles.userEmail}>{user?.email}</Text>
            <Text style={styles.userStatus}>Signed in</Text>
          </View>
        </View>
      </View>

      {/* Connections */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connected Accounts</Text>

        <TouchableOpacity style={styles.connectionItem} onPress={handleConnectGoogle}>
          <View style={styles.connectionLeft}>
            <View style={[styles.connectionIcon, { backgroundColor: 'rgba(234, 67, 53, 0.15)' }]}>
              <Ionicons name="logo-google" size={20} color="#EA4335" />
            </View>
            <View>
              <Text style={styles.connectionName}>Google</Text>
              <Text style={styles.connectionStatus}>
                {user?.googleConnected ? 'Connected' : 'Not connected'}
              </Text>
            </View>
          </View>
          {user?.googleConnected ? (
            <Ionicons name="checkmark-circle" size={24} color="#22c55e" />
          ) : (
            <Ionicons name="add-circle-outline" size={24} color="#888" />
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.connectionItem} onPress={handleConnectMicrosoft}>
          <View style={styles.connectionLeft}>
            <View style={[styles.connectionIcon, { backgroundColor: 'rgba(0, 120, 212, 0.15)' }]}>
              <Ionicons name="logo-microsoft" size={20} color="#0078D4" />
            </View>
            <View>
              <Text style={styles.connectionName}>Microsoft</Text>
              <Text style={styles.connectionStatus}>
                {user?.microsoftConnected ? 'Connected' : 'Not connected'}
              </Text>
            </View>
          </View>
          {user?.microsoftConnected ? (
            <Ionicons name="checkmark-circle" size={24} color="#22c55e" />
          ) : (
            <Ionicons name="add-circle-outline" size={24} color="#888" />
          )}
        </TouchableOpacity>
      </View>

      {/* About */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.aboutCard}>
          <View style={styles.logoSmall}>
            <Ionicons name="sparkles" size={24} color="#f59e0b" />
          </View>
          <Text style={styles.appName}>Donna</Text>
          <Text style={styles.appVersion}>Version 1.0.0</Text>
          <Text style={styles.appTagline}>Your AI Executive Assistant</Text>
        </View>
      </View>

      {/* Sign Out */}
      <View style={styles.section}>
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={20} color="#ef4444" />
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0f',
  },
  section: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a24',
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  userCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  userInfo: {
    flex: 1,
  },
  userEmail: {
    fontSize: 16,
    fontWeight: '600',
    color: '#e5e5e5',
  },
  userStatus: {
    fontSize: 13,
    color: '#22c55e',
    marginTop: 2,
  },
  connectionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    backgroundColor: '#1a1a24',
    borderRadius: 12,
    marginBottom: 8,
  },
  connectionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  connectionIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  connectionName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#e5e5e5',
  },
  connectionStatus: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
  aboutCard: {
    alignItems: 'center',
    padding: 24,
    backgroundColor: '#1a1a24',
    borderRadius: 12,
  },
  logoSmall: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  appName: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  appVersion: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  appTagline: {
    fontSize: 13,
    color: '#888',
    marginTop: 8,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderRadius: 12,
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ef4444',
  },
});


