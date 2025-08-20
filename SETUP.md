# Quick Setup Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend  
cd frontend
npm install
```

### 2. Configure Twilio Credentials

```bash
cd backend
cp env_template.txt .env
```

Edit `.env` with your credentials:

```env
# Required
TWILIO_ACCOUNT_SID=Your main acount sid

# Option 1: Auth Token (Primary - Full Permissions)
TWILIO_AUTH_TOKEN=your_auth_token_here

# Option 2: API Key (Fallback - More Secure)
TWILIO_API_KEY_SID=Your SID here
TWILIO_API_KEY_SECRET=your_secret_here

# Phone Numbers
TWILIO_NUMBER_A=+1234567890
TWILIO_NUMBER_B=+1234567890
```

### 3. Test Your Setup

```bash
cd backend
python test_auth.py
```

✅ **Success**: You'll see "SETUP READY: Your Twilio configuration is valid!"

### 4. Run the Application

```bash
# Terminal 1: Backend
cd backend
python app.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser!

## 🔐 How Dual Authentication Works

1. **Auth Token** is tried first (has full permissions, more reliable)
2. If it fails, **API Key** is automatically used
3. No restart needed - seamless fallback
4. Real-time status monitoring shows which method is active

## 🆘 Need Help?

- **Test script fails**: Check your `.env` file and Twilio credentials
- **Can't make calls**: Verify phone numbers are configured
- **Authentication errors**: Ensure credentials have proper permissions

## 📱 Get Twilio Credentials

- **Account SID**: [Twilio Console](https://console.twilio.com/us1/account)
- **API Key**: [API Keys](https://console.twilio.com/us1/account/keys-credentials/api-keys)
- **Auth Token**: [Auth Tokens](https://console.twilio.com/us1/account/keys-credentials/auth-tokens)
