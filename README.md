# Twilio Call Bridge – Complete Beginner Guide

This project lets you place and receive real phone calls using your Twilio number. It first calls your phone (agent), and when you answer it dials the customer and bridges you together for real‑time conversation.

You control calls from the browser, but the audio is on real phones (not in the browser).

---

## 0) What you need (once)
- A Twilio account and one purchased Twilio phone number (recommended: non‑toll‑free local number)
- Windows, macOS or Linux
- Node.js 18+ and npm
- Python 3.10+ (Conda compatible)
- An ngrok account (free) to expose your local backend to Twilio

Useful links:
- Twilio Console: `https://console.twilio.com`
- Buy a number: Twilio Console → Phone Numbers → Buy a number
- ngrok: `https://dashboard.ngrok.com`

---

## 1) Clone and install
```bash
# open a terminal
cd C:\Users\<you>\Desktop\Alexproject\twillioCall\twillioCall

# Backend deps (inside conda later, see step 2)
cd backend
pip install -r requirements.txt

# Frontend deps
cd ..\frontend
npm install
```

---

## 2) Create/activate a Conda env (Python)
```bash
# Create (first time only)
conda create -n twiliocall python=3.11 -y

# Activate
conda activate twiliocall
```

---

## 3) Configure environment (.env)
1) Copy the template and edit values
```bash
cd backend
copy env_template.txt .env
```

2) Open `backend/.env` and fill:
```env
# Required Twilio credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here            # Primary method
# Optional fallback (API Key)
TWILIO_API_KEY_SID=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_KEY_SECRET=your_api_key_secret_here

# Your numbers
TWILIO_NUMBER_A=+1XXXXXXXXXX     # Your Twilio number (caller ID / the number people call)
TWILIO_NUMBER_B=+9XXXXXXXXXXX    # Your mobile (rings first as the agent)

# URLs
FRONTEND_URL=http://localhost:5173
BACKEND_URL=https://<your-ngrok>.ngrok-free.app   # set after Step 5; update whenever ngrok URL changes
CORS_ORIGIN=http://localhost:5173
FLASK_SECRET=change-me
```

Notes:
- `TWILIO_NUMBER_A` should be a non‑toll‑free local number for the most reliable international calling.
- If your Twilio project is Trial, all destination phones must be verified (Console → Phone Numbers → Verified caller IDs) or upgrade your account and add balance.

---

## 4) Start the backend (Flask)
```bash
# In a terminal with conda env active
cd backend
python app.py
```
You should see “Running on http://127.0.0.1:5000”. Keep this terminal open.

---

## 5) Start ngrok and set BACKEND_URL
```bash
# New terminal (backend still running)
ngrok config add-authtoken <YOUR_NGROK_TOKEN>   # one time
ngrok http 5000
```
Copy the HTTPS forwarding URL (looks like `https://abc123.ngrok-free.app`), then edit `backend/.env` and set:
```env
BACKEND_URL=https://abc123.ngrok-free.app
```
Restart the backend so it picks up the new URL:
```bash
# In the backend terminal, stop with Ctrl+C then:
python app.py
```

---

## 6) Point your Twilio number webhooks to your ngrok URL
Twilio Console → Phone Numbers → Your Number → Voice → Configure with “Webhook”. Set:
- A call comes in: `https://abc123.ngrok-free.app/api/voice/incoming/a` (HTTP POST)
- Call status changes: `https://abc123.ngrok-free.app/api/voice/status` (HTTP POST)
Click Save.

These webhooks allow inbound calls to reach your app and let you see live status updates.

---

## 7) Start the frontend (browser UI)
```bash
# New terminal
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 8) Make an outbound call (you → friend)
In the UI:
- Customer number: your friend’s phone (E.164 format, e.g., `+92310...`)
- Agent number: leave empty to use `TWILIO_NUMBER_B` (your mobile)
- Click “Call”

Flow:
1) Your mobile (agent) rings from your Twilio number (`TWILIO_NUMBER_A`). Answer it.
2) Twilio then dials the customer and bridges the call. You both talk on phones.

Implementation detail: the app sends inline TwiML for bridging; no external fetch is needed for the bridge step.

---

## 9) Receive an inbound call (someone calls your Twilio number)
Give someone your Twilio number (`TWILIO_NUMBER_A`). When they call:
1) Twilio hits `/api/voice/incoming/a`
2) Your app dials `TWILIO_NUMBER_B` (your mobile) and bridges the caller to you
3) Answer your mobile to talk

Make sure the “A call comes in” webhook (Step 6) points to your current ngrok URL.

---

## 10) Country/permission notes (very important)
- Trial projects: You can only call verified numbers until you upgrade and add credit.
- Geo‑permissions: To call certain countries (e.g., Pakistan), enable them in Console → Voice → Settings → Calling Geographic Permissions → Low‑risk. Save.
- Toll‑free caller ID: Many carriers reject international calls from toll‑free numbers. Prefer a local Twilio number as `TWILIO_NUMBER_A` for international dialing/forwarding.
- E.164 format: Always use `+<countrycode><number>` (e.g., `+18559641121`).

---

## 11) Quick health checks
- Frontend shows “Twilio Connected” on the status card.
- Backend terminal shows requests like `POST /api/call/connect 200` and `POST /api/voice/status 204`.
- ngrok inspector `http://127.0.0.1:4040` should show incoming requests to `/api/voice/incoming/a` (inbound) and `/api/voice/status`.

---

## 12) Troubleshooting
- “Application error” when you answer: ensure `BACKEND_URL` matches your current ngrok URL and you restarted the backend; confirm webhooks are set to the same URL; check ngrok inspector for errors.
- Error 21210 (source number not allowed): Your caller ID must be your Twilio number. Set `TWILIO_NUMBER_A` to your Twilio number; do not use your personal mobile as `from_`.
- Error 21215 (geo‑permissions): Enable the destination country in Voice → Geo‑permissions; on Trial also verify the numbers or upgrade.
- Call rings agent but not customer: check country permissions, number format, and whether your Twilio number is toll‑free (use a local number instead).
- Events connection error in UI: refresh the page; it’s the SSE stream reconnecting.
- ngrok URL changed after restart: update `BACKEND_URL` in `.env` and Twilio webhooks, then restart backend.

---

## 13) Security
- Never commit real credentials. `.env` is ignored by git.
- API Key is optional; the app tries Auth Token first and falls back to API Key automatically.

---

## 14) FAQ
- “Where do I speak?” On your phones. The browser is only a controller and status dashboard.
- “Can I talk through the browser?” Not in this project. That requires Twilio Voice WebRTC (JS SDK). We can add it later if you need browser audio.

---

## 15) Project scripts (summary)
```bash
# Backend
conda activate twiliocall
cd backend
python app.py

# ngrok (new terminal)
ngrok http 5000
# then set BACKEND_URL in backend/.env and restart backend

# Frontend (new terminal)
cd frontend
npm run dev
```

You’re ready. Start the backend, start ngrok, point Twilio webhooks, start the frontend, and click “Call”.
