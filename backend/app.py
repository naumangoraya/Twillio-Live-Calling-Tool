import json
import os
import queue
from urllib.parse import urlencode

from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial, Say


# Load environment variables from project root .env if present
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

app = Flask(__name__)

# Configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", FRONTEND_URL)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_API_KEY_SID = os.getenv("TWILIO_API_KEY_SID", "")
TWILIO_API_KEY_SECRET = os.getenv("TWILIO_API_KEY_SECRET", "")

TWILIO_NUMBER_A = os.getenv("TWILIO_NUMBER_A", "")
TWILIO_NUMBER_B = os.getenv("TWILIO_NUMBER_B", "")

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "dev-secret-change-me")

CORS(app, resources={r"/api/*": {"origins": CORS_ORIGIN}})


# Twilio REST client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_API_KEY_SID and TWILIO_API_KEY_SECRET:
    twilio_client = Client(TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET, TWILIO_ACCOUNT_SID)


# Simple in-memory subscribers for Server-Sent Events
subscribers = set()


def broadcast_event(event_type: str, payload: dict) -> None:
    data = {"event": event_type, "payload": payload}
    for q in list(subscribers):
        try:
            q.put_nowait(data)
        except Exception:
            # Best-effort; skip on failure
            pass


@app.get("/api/health")
def health() -> Response:
    return jsonify({
        "status": "ok",
        "twilio_configured": bool(twilio_client and TWILIO_NUMBER_A and TWILIO_NUMBER_B),
        "twilio_auth_method": "api_key" if (TWILIO_API_KEY_SID and TWILIO_API_KEY_SECRET) else "auth_token"
    })


@app.get("/api/events")
def sse_events() -> Response:
    q: queue.Queue = queue.Queue()
    subscribers.add(q)

    def stream():
        try:
            # Immediate hello event so client knows we're connected
            yield f"data: {json.dumps({'event': 'connected', 'payload': {}})}\n\n"
            while True:
                data = q.get()
                yield f"data: {json.dumps(data)}\n\n"
        except GeneratorExit:
            pass
        finally:
            subscribers.discard(q)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return Response(stream(), headers=headers)


@app.post("/api/call/connect")
def create_outbound_call() -> Response:
    if twilio_client is None:
        return jsonify({"error": "Twilio is not configured. Check environment variables."}), 400

    body = request.get_json(silent=True) or {}
    customer_number = (body.get("customer_number") or "").strip()
    agent_number = (body.get("agent_number") or TWILIO_NUMBER_B).strip()

    if not customer_number:
        return jsonify({"error": "customer_number is required"}), 400
    if not agent_number:
        return jsonify({"error": "agent_number is required (or TWILIO_NUMBER_B must be set)"}), 400
    if not TWILIO_NUMBER_A:
        return jsonify({"error": "TWILIO_NUMBER_A is not configured"}), 400

    # We'll first call the agent_number, and when they answer, Twilio will hit the
    # bridge endpoint which dials the customer_number to connect both parties.
    bridge_params = {"customer": customer_number}
    bridge_url = f"{BACKEND_URL}/api/voice/bridge?{urlencode(bridge_params)}"

    try:
        call = twilio_client.calls.create(
            to=agent_number,
            from_=TWILIO_NUMBER_A,
            url=bridge_url,
            status_callback=f"{BACKEND_URL}/api/voice/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            status_callback_method="POST",
        )
        broadcast_event("call_initiated", {"to": agent_number, "customer": customer_number, "sid": call.sid})
        return jsonify({"sid": call.sid})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/voice/bridge")
def voice_bridge() -> Response:
    """TwiML: once the agent answers, dial out to the customer and bridge."""
    customer = (request.args.get("customer") or "").strip()
    vr = VoiceResponse()
    if not customer:
        vr.say("Customer number missing. Goodbye.")
        return Response(str(vr), mimetype="text/xml")

    dial = Dial(caller_id=TWILIO_NUMBER_A)
    dial.number(customer)
    vr.append(dial)
    return Response(str(vr), mimetype="text/xml")


@app.post("/api/voice/incoming/a")
def inbound_a() -> Response:
    """Webhook for incoming calls to TWILIO_NUMBER_A."""
    from_num = request.form.get("From", "")
    to_num = request.form.get("To", "")
    sid = request.form.get("CallSid", "")
    broadcast_event("incoming_call", {"to": to_num, "from": from_num, "sid": sid, "which": "A"})

    vr = VoiceResponse()
    if TWILIO_NUMBER_B:
        dial = Dial(caller_id=TWILIO_NUMBER_A)
        dial.number(TWILIO_NUMBER_B)
        vr.append(dial)
    else:
        vr.say("No destination configured for this number.")
    return Response(str(vr), mimetype="text/xml")


@app.post("/api/voice/incoming/b")
def inbound_b() -> Response:
    """Webhook for incoming calls to TWILIO_NUMBER_B."""
    from_num = request.form.get("From", "")
    to_num = request.form.get("To", "")
    sid = request.form.get("CallSid", "")
    broadcast_event("incoming_call", {"to": to_num, "from": from_num, "sid": sid, "which": "B"})

    vr = VoiceResponse()
    if TWILIO_NUMBER_A:
        dial = Dial(caller_id=TWILIO_NUMBER_B)
        dial.number(TWILIO_NUMBER_A)
        vr.append(dial)
    else:
        vr.say("No destination configured for this number.")
    return Response(str(vr), mimetype="text/xml")


@app.post("/api/voice/status")
def status_callback() -> Response:
    payload = {
        "CallSid": request.form.get("CallSid"),
        "CallStatus": request.form.get("CallStatus"),
        "To": request.form.get("To"),
        "From": request.form.get("From"),
        "Timestamp": request.form.get("Timestamp"),
    }
    broadcast_event("call_status", payload)
    return ("", 204)


def run_app():
    # Bind on all interfaces so ngrok can tunnel
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    run_app()


