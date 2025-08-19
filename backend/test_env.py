import os
from dotenv import load_dotenv

# Load environment variables from project root .env if present
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

print("Environment Variables Check:")
print("=" * 40)
print(f"TWILIO_ACCOUNT_SID: {os.getenv('TWILIO_ACCOUNT_SID', 'NOT SET')}")
print(f"TWILIO_API_KEY_SID: {os.getenv('TWILIO_API_KEY_SID', 'NOT SET')}")
print(f"TWILIO_API_KEY_SECRET: {os.getenv('TWILIO_API_KEY_SECRET', 'NOT SET')}")
print(f"TWILIO_NUMBER_A: {os.getenv('TWILIO_NUMBER_A', 'NOT SET')}")
print(f"TWILIO_NUMBER_B: {os.getenv('TWILIO_NUMBER_B', 'NOT SET')}")
print("=" * 40)

# Check if we can create a Twilio client
try:
    from twilio.rest import Client
    if os.getenv('TWILIO_ACCOUNT_SID') and os.getenv('TWILIO_API_KEY_SID') and os.getenv('TWILIO_API_KEY_SECRET'):
        client = Client(os.getenv('TWILIO_API_KEY_SID'), os.getenv('TWILIO_API_KEY_SECRET'), os.getenv('TWILIO_ACCOUNT_SID'))
        print("✅ Twilio client created successfully!")
    else:
        print("❌ Missing required Twilio environment variables")
except Exception as e:
    print(f"❌ Error creating Twilio client: {e}")

