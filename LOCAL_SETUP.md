# Local Development Setup with Render API

## Quick Setup

Your backend is now deployed on Render, so you can use it from anywhere! Here's how to configure your desktop and mobile apps.

---

## Step 1: Get Your Render API URL

1. Go to your [Render Dashboard](https://dashboard.render.com)
2. Click on your backend service
3. Copy the URL (e.g., `https://donna-backend.onrender.com`)

---

## Step 2: Desktop App Setup

### Option A: Use Render API (Recommended - No Local Backend Needed!)

1. **Create `.env` file** in `desktop/` directory:
   ```bash
   cd desktop
   ```

2. **Copy the example**:
   ```bash
   copy .env.example .env  # Windows
   # or
   cp .env.example .env    # macOS/Linux
   ```

3. **Edit `.env`** and add your Render URL:
   ```
   VITE_API_URL=https://your-app-name.onrender.com
   ```

4. **Run the app**:
   ```bash
   npm run tauri dev
   ```

The app will now connect to your Render API! 🎉

### Option B: Use Local Backend (If you want to test locally)

1. Make sure your local backend is running:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Edit `desktop/.env`**:
   ```
   VITE_API_URL=http://localhost:8000
   ```

---

## Step 3: Mobile App Setup

### Option A: Use Render API (Recommended - Works from Anywhere!)

1. **Create `.env` file** in `mobile/` directory:
   ```bash
   cd mobile
   ```

2. **Copy the example**:
   ```bash
   copy .env.example .env  # Windows
   # or
   cp .env.example .env    # macOS/Linux
   ```

3. **Edit `.env`** and add your Render URL:
   ```
   EXPO_PUBLIC_API_URL=https://your-app-name.onrender.com
   ```

4. **Run the app**:
   ```bash
   npm start
   # or
   npx expo start
   ```

The mobile app will now connect to your Render API! 📱✨

### Option B: Use Local Backend (For Testing)

If you want to test against your local backend:

1. **Edit `mobile/.env`**:
   ```
   EXPO_PUBLIC_API_URL=http://localhost:8000
   EXPO_PUBLIC_USE_LOCAL=true
   ```

   **For physical devices**, use your PC's IP address:
   ```
   EXPO_PUBLIC_API_URL=http://192.168.1.XXX:8000
   EXPO_PUBLIC_USE_LOCAL=true
   ```

   To find your PC's IP:
   - Windows: `ipconfig` (look for IPv4 Address)
   - macOS/Linux: `ifconfig` or `ip addr`

---

## Benefits of Using Render API

✅ **No local backend needed** - Just run the apps!  
✅ **Works from anywhere** - Home, office, coffee shop  
✅ **Always available** - Backend runs 24/7 on Render  
✅ **HTTPS secure** - All connections are encrypted  
✅ **Easy sharing** - Anyone can use your apps with your API  

---

## Switching Between Local and Render

Just update the `.env` file:

**Use Render API:**
```
VITE_API_URL=https://your-app-name.onrender.com
```

**Use Local Backend:**
```
VITE_API_URL=http://localhost:8000
```

Then restart the app!

---

## Testing

1. **Desktop App**: Run `npm run tauri dev` - should connect to Render API
2. **Mobile App**: Run `npm start` - scan QR code, should connect to Render API
3. **Check logs**: Look for `[API] Using backend: https://...` in console

---

## Troubleshooting

**App can't connect:**
- Check your Render URL is correct
- Make sure Render service is running (check dashboard)
- Check browser console/Expo logs for errors

**Want to test locally:**
- Make sure local backend is running on port 8000
- Update `.env` to use `http://localhost:8000`
- Restart the app

