import json
import os
import queue
import logging
from urllib.parse import urlencode

from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial, Say
from twilio.base.exceptions import TwilioException, TwilioRestException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


class TwilioClientManager:
    """Manages Twilio client with fallback authentication methods"""
    
    def __init__(self):
        self.primary_client = None
        self.fallback_client = None
        self.current_method = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize both authentication methods"""
        # Try Auth Token first (has full permissions, more reliable)
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                self.primary_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                self.current_method = "auth_token"
                logger.info("Primary Twilio client initialized with Auth Token authentication")
            except Exception as e:
                logger.warning(f"Failed to initialize Auth Token client: {e}")
                self.primary_client = None
        
        # Try API Key as fallback (more secure but may have permission restrictions)
        if TWILIO_ACCOUNT_SID and TWILIO_API_KEY_SID and TWILIO_API_KEY_SECRET:
            try:
                self.fallback_client = Client(TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET, TWILIO_ACCOUNT_SID)
                if not self.primary_client:
                    self.current_method = "api_key"
                    logger.info("Fallback Twilio client initialized with API Key authentication")
                else:
                    logger.info("Fallback Twilio client initialized with API Key (backup)")
            except Exception as e:
                logger.warning(f"Failed to initialize API Key client: {e}")
                self.fallback_client = None
    
    def get_client(self):
        """Get the current working client"""
        return self.primary_client or self.fallback_client
    
    def get_auth_method(self):
        """Get current authentication method"""
        if self.primary_client:
            return "auth_token"
        elif self.fallback_client:
            return "api_key"
        return "none"
    
    def test_connection(self):
        """Test the current client connection"""
        client = self.get_client()
        if not client:
            return False, "No Twilio client available"
        
        try:
            # Try to fetch account info to test connection
            account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
            return True, f"Connected using {self.get_auth_method()} authentication"
        except TwilioRestException as e:
            if e.code == 20003:  # Authentication error
                # Try to switch to fallback if available
                if self.primary_client and self.fallback_client and self.current_method == "auth_token":
                    logger.warning("Auth Token authentication failed, switching to API Key")
                    self.current_method = "api_key"
                    return self.test_connection()
                else:
                    return False, f"Authentication failed: {e.msg}"
            else:
                return False, f"Twilio error: {e.msg}"
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"


# Initialize Twilio client manager
twilio_manager = TwilioClientManager()

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
    # Test connection and get current status
    is_connected, message = twilio_manager.test_connection()
    
    return jsonify({
        "status": "ok" if is_connected else "error",
        "twilio_configured": bool(twilio_manager.get_client() and TWILIO_NUMBER_A and TWILIO_NUMBER_B),
        "twilio_auth_method": twilio_manager.get_auth_method(),
        "twilio_connection_status": message,
        "twilio_connected": is_connected
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
    # Test connection before proceeding
    is_connected, message = twilio_manager.test_connection()
    if not is_connected:
        return jsonify({"error": f"Twilio connection failed: {message}"}), 500
    
    client = twilio_manager.get_client()
    if client is None:
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

    # We'll first call the agent_number, and when they answer, Twilio will dial the
    # customer_number to connect both parties. We provide inline TwiML so Twilio does
    # not need to fetch our bridge URL.
    bridge_twiml = (
        f"<Response>"
        f"<Dial callerId=\"{TWILIO_NUMBER_A}\">"
        f"<Number>{customer_number}</Number>"
        f"</Dial>"
        f"</Response>"
    )

    try:
        call = client.calls.create(
            to=agent_number,
            from_=TWILIO_NUMBER_A,
            twiml=bridge_twiml,
            status_callback=f"{BACKEND_URL}/api/voice/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            status_callback_method="POST",
        )
        
        auth_method = twilio_manager.get_auth_method()
        broadcast_event("call_initiated", {
            "to": agent_number, 
            "customer": customer_number, 
            "sid": call.sid,
            "auth_method": auth_method
        })
        
        logger.info(f"Call initiated successfully using {auth_method} authentication")
        return jsonify({
            "sid": call.sid,
            "auth_method": auth_method,
            "message": "Call initiated successfully"
        })
        
    except TwilioRestException as e:
        error_msg = f"Twilio error (code {e.code}): {e.msg}"
        logger.error(error_msg)
        
        # If this is an authentication error and we have a fallback, try to switch
        if e.code == 20003 and twilio_manager.fallback_client and twilio_manager.current_method == "auth_token":
            logger.info("Attempting to retry with fallback authentication")
            twilio_manager.current_method = "api_key"
            # Recursive call to retry with fallback
            return create_outbound_call()
        
        return jsonify({"error": error_msg}), 500
        
    except Exception as exc:
        error_msg = f"Unexpected error: {str(exc)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500


@app.route("/api/voice/bridge", methods=["GET", "POST"])
def voice_bridge() -> Response:
    """TwiML: once the agent answers, dial out to the customer and bridge."""
    customer = (request.values.get("customer") or "").strip()
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


@app.get("/api/twilio/status")
def twilio_status() -> Response:
    """Get detailed Twilio connection status"""
    is_connected, message = twilio_manager.test_connection()
    
    return jsonify({
        "connected": is_connected,
        "message": message,
        "current_auth_method": twilio_manager.get_auth_method(),
        "primary_client_available": bool(twilio_manager.primary_client),
        "fallback_client_available": bool(twilio_manager.fallback_client),
        "account_sid_configured": bool(TWILIO_ACCOUNT_SID),
        "api_key_configured": bool(TWILIO_API_KEY_SID and TWILIO_API_KEY_SECRET),
        "auth_token_configured": bool(TWILIO_AUTH_TOKEN)
    })


def run_app():
    # Bind on all interfaces so ngrok can tunnel
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    run_app()


