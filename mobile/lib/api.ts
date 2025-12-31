import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import Constants from 'expo-constants';

// ===========================================
// 🔧 CONFIGURATION - Update this to your PC's IP address
// ===========================================
const YOUR_PC_IP = '192.168.1.177'; // ← CHANGE THIS to your computer's IP (run 'ipconfig' to find it)
// ===========================================

// Auto-detect the correct API URL based on environment
const getApiBase = () => {
  // Production API from environment variable
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  
  // Development - use localhost or PC IP
  if (__DEV__) {
    if (Platform.OS === 'web') {  
      return 'http://localhost:8000';
    }
    
    if (Platform.OS === 'android') {
      // Check if running in emulator
      if (Constants.isDevice === false) {
        return 'http://10.0.2.2:8000'; // Android emulator -> host machine
      }
    }
    
    // Physical device (iOS or Android) - use your PC's IP
    return `http://${YOUR_PC_IP}:8000`;
  }
  
  // Default to production (update with your Render URL)
  return 'https://your-app-name.onrender.com';
};

const API_BASE = getApiBase();
console.log(`[API] Using backend: ${API_BASE}`);

class ApiClient {
  private token: string | null = null;

  async init() {
    this.token = await SecureStore.getItemAsync('token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      SecureStore.setItemAsync('token', token);
    } else {
      SecureStore.deleteItemAsync('token');
    }
  }

  getToken() {
    return this.token;
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  async get(endpoint: string) {
    return this.request(endpoint, { method: 'GET' });
  }

  async post(endpoint: string, data: any) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

export const api = new ApiClient();

