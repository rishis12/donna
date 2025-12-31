# Client App Deployment Guide

## Architecture Overview

Your Donna AI system has **3 parts**:

1. **Backend API** (✅ Deployed on Render) - The server/API
2. **Desktop App** (Tauri + React) - Users install this on their computers
3. **Mobile App** (React Native + Expo) - Users install this on their phones

**Users need the Desktop/Mobile apps to actually use your service!**

---

## Step 1: Update Apps to Use Deployed API

Both apps currently point to `localhost:8000`. Update them to use your Render API URL.

### Get Your Render API URL

Your backend is deployed at: `https://your-app-name.onrender.com` (check your Render dashboard)

---

## Step 2: Desktop App Configuration

### Option A: Environment Variable (Recommended)

Update `desktop/src/lib/api.ts`:

```typescript
// Use environment variable or default to production API
const API_BASE = import.meta.env.VITE_API_URL || 'https://your-app-name.onrender.com'
```

Then create `.env` in `desktop/`:
```
VITE_API_URL=https://your-app-name.onrender.com
```

For local development:
```
VITE_API_URL=http://localhost:8000
```

### Option B: Direct Update

Update `desktop/src/lib/api.ts` line 1:
```typescript
const API_BASE = 'https://your-app-name.onrender.com'
```

---

## Step 3: Mobile App Configuration

Update `mobile/lib/api.ts`:

```typescript
// Auto-detect the correct API URL based on environment
const getApiBase = () => {
  // Production API
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  
  // Development - use localhost or PC IP
  if (__DEV__) {
    if (Platform.OS === 'web') {
      return 'http://localhost:8000';
    }
    // ... rest of dev logic
  }
  
  // Default to production
  return 'https://your-app-name.onrender.com';
};
```

Create `.env` in `mobile/`:
```
EXPO_PUBLIC_API_URL=https://your-app-name.onrender.com
```

---

## Step 4: Build Desktop App

### Windows
```bash
cd desktop
npm run tauri build
# Output: desktop/src-tauri/target/release/donna.exe (or .app for macOS)
```

### macOS
```bash
cd desktop
npm run tauri build
# Output: desktop/src-tauri/target/release/bundle/macos/Donna.app
```

### Linux
```bash
cd desktop
npm run tauri build
# Output: desktop/src-tauri/target/release/bundle/appimage/donna.AppImage
```

### Distribution
- **Windows**: Share the `.exe` file
- **macOS**: Share the `.app` bundle or create a `.dmg`
- **Linux**: Share the `.AppImage` or create `.deb`/`.rpm` packages

---

## Step 5: Build Mobile App

### Development Build (Expo)
```bash
cd mobile
npx expo start
# Scan QR code with Expo Go app on your phone
```

### Production Build (EAS Build - Recommended)

1. **Install EAS CLI**
   ```bash
   npm install -g eas-cli
   eas login
   ```

2. **Configure EAS**
   ```bash
   cd mobile
   eas build:configure
   ```

3. **Build for iOS**
   ```bash
   eas build --platform ios
   ```

4. **Build for Android**
   ```bash
   eas build --platform android
   ```

5. **Submit to Stores**
   ```bash
   eas submit --platform ios    # Submit to App Store
   eas submit --platform android # Submit to Play Store
   ```

---

## Step 6: Distribution Options

### Desktop App
1. **Direct Download**: Host `.exe`/`.app`/`.AppImage` on your website
2. **GitHub Releases**: Upload builds as GitHub releases
3. **Auto-Updater**: Implement Tauri auto-updater (advanced)

### Mobile App
1. **App Stores**: Submit to Apple App Store and Google Play Store
2. **TestFlight (iOS)**: Beta testing before App Store release
3. **Internal Testing (Android)**: Share APK for testing
4. **Expo Updates**: OTA updates without app store approval (for JS changes)

---

## Quick Start Summary

1. ✅ Backend deployed on Render
2. 🔧 Update API URLs in `desktop/src/lib/api.ts` and `mobile/lib/api.ts`
3. 🏗️ Build desktop app: `cd desktop && npm run tauri build`
4. 📱 Build mobile app: `cd mobile && eas build --platform all`
5. 📦 Distribute to users

---

## Testing Locally

Before building for production:

1. **Test Desktop App**
   ```bash
   cd desktop
   npm run tauri dev
   ```

2. **Test Mobile App**
   ```bash
   cd mobile
   npx expo start
   ```

Both should connect to your Render API when configured correctly!

