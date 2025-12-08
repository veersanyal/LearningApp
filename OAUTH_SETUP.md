# OAuth Setup Guide

## ✅ Implementation Complete!

OAuth login with Google has been added to your app. Here's how to set it up:

---

## 🔵 Google Sign In Setup

### Step 1: Create Google OAuth Credentials

1. Go to **Google Cloud Console**: https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable **Google+ API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google+ API" and enable it
4. Create OAuth 2.0 Credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Web application**
   - Name: "StudyBoiler"
   - Authorized JavaScript origins:
     - `https://web-production-69b94.up.railway.app`
     - `http://localhost:5000` (for local testing)
   - Authorized redirect URIs:
     - `https://web-production-69b94.up.railway.app/auth/google/callback`
     - `http://localhost:5000/auth/google/callback` (for local testing)
5. **Copy the Client ID** (looks like: `123456789-abc.apps.googleusercontent.com`)

### Step 2: Add to Railway Environment Variables

1. Go to Railway → Your project → "web" service
2. Click **"Variables"** tab
3. Add new variable:
   - Name: `GOOGLE_CLIENT_ID`
   - Value: Your Google Client ID from Step 1
4. Save

### Step 3: Test

1. Refresh your app
2. Click "Continue with Google"
3. Select your Google account
4. You should be logged in!

---

## 🚀 Quick Start

1. **Get Google Client ID** (follow Step 1 above)
2. **Add to Railway**: `GOOGLE_CLIENT_ID=your-client-id-here`
3. **Redeploy** - Railway will auto-deploy
4. **Test** - Click "Continue with Google" button

---

## 📝 Current Status

✅ **Backend OAuth routes** - Implemented  
✅ **Database schema** - Updated for OAuth  
✅ **Frontend buttons** - Added to login modal  
✅ **Google OAuth** - Ready (needs Client ID)  

---

## 🔧 How It Works

### Google OAuth Flow:
1. User clicks "Continue with Google"
2. Google Identity Services shows sign-in popup
3. User selects Google account
4. Google returns JWT credential token
5. Frontend sends token to `/auth/google`
6. Backend verifies token and extracts user info
7. User is created/logged in automatically

---

## ⚠️ Important Notes

1. **Google Client ID is required** for Google Sign In to work
2. **OAuth users** don't have passwords - they can only log in via OAuth
3. **Email addresses** from OAuth are used as unique identifiers
4. **Username** is auto-generated from email if not provided

---

## 🐛 Troubleshooting

### "Google Sign In not configured"
- Make sure `GOOGLE_CLIENT_ID` is set in Railway
- Check that the Client ID is correct
- Verify authorized origins include your Railway URL

### "Invalid Google token"
- Check that the Client ID matches
- Verify authorized redirect URIs are correct
- Make sure Google+ API is enabled

---

## 📚 Resources

- **Google OAuth Docs**: https://developers.google.com/identity/gsi/web
- **Railway Environment Variables**: https://docs.railway.app/develop/variables

---

**Once you add the `GOOGLE_CLIENT_ID` to Railway, Google Sign In will work immediately!** 🚀
