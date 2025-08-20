#!/usr/bin/env python3
"""
Twilio Authentication Test Script

This script tests your Twilio credentials to ensure they work before running the main application.
Run this script to verify your setup before starting the Flask app.

Usage:
    python test_auth.py
"""

import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioException, TwilioRestException

def load_environment():
    """Load environment variables from .env file"""
    # Try to load from current directory first
    if os.path.exists('.env'):
        load_dotenv('.env')
        print("✓ Loaded .env file from current directory")
    # Try to load from parent directory
    elif os.path.exists('../.env'):
        load_dotenv('../.env')
        print("✓ Loaded .env file from parent directory")
    else:
        print("⚠ No .env file found. Make sure to create one based on env_template.txt")
        return False
    return True

def test_credentials():
    """Test Twilio credentials and return results"""
    results = {
        'account_sid': False,
        'api_key': False,
        'auth_token': False,
        'api_key_client': None,
        'auth_token_client': None,
        'errors': []
    }
    
    # Check Account SID
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    if account_sid:
        results['account_sid'] = True
        print(f"✓ Account SID: {account_sid[:10]}...")
    else:
        results['errors'].append("TWILIO_ACCOUNT_SID not found")
        print("✗ Account SID: Not configured")
    
    # Test Auth Token authentication (Primary method)
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    
    if auth_token:
        results['auth_token'] = True
        print(f"✓ Auth Token: {'*' * len(auth_token)}")
        
        try:
            client = Client(account_sid, auth_token)
            # Test connection by fetching account info
            account = client.api.accounts(account_sid).fetch()
            results['auth_token_client'] = client
            print(f"✓ Auth Token authentication: SUCCESS (Account: {account.friendly_name})")
        except TwilioRestException as e:
            if e.code == 20003:
                results['errors'].append(f"Auth Token authentication failed: {e.msg}")
                print(f"✗ Auth Token authentication: FAILED - Authentication error")
            else:
                results['errors'].append(f"Auth Token error: {e.msg}")
                print(f"✗ Auth Token authentication: FAILED - {e.msg}")
        except Exception as e:
            results['errors'].append(f"Auth Token error: {str(e)}")
            print(f"✗ Auth Token authentication: FAILED - {str(e)}")
    else:
        print("⚠ Auth Token: Not configured (primary method)")
    
    # Test API Key authentication (Fallback method)
    api_key_sid = os.getenv('TWILIO_API_KEY_SID')
    api_key_secret = os.getenv('TWILIO_API_KEY_SECRET')
    
    if api_key_sid and api_key_secret:
        results['api_key'] = True
        print(f"✓ API Key SID: {api_key_sid[:10]}...")
        print(f"✓ API Key Secret: {'*' * len(api_key_secret)}")
        
        try:
            client = Client(api_key_sid, api_key_secret, account_sid)
            # Test connection by fetching account info
            account = client.api.accounts(account_sid).fetch()
            results['api_key_client'] = client
            print(f"✓ API Key authentication: SUCCESS (Account: {account.friendly_name})")
        except TwilioRestException as e:
            if e.code == 20003:
                results['errors'].append(f"API Key authentication failed: {e.msg}")
                print(f"✗ API Key authentication: FAILED - Authentication error")
            else:
                results['errors'].append(f"API Key error: {e.msg}")
                print(f"✗ API Key authentication: FAILED - {e.msg}")
        except Exception as e:
            results['errors'].append(f"API Key error: {str(e)}")
            print(f"✗ API Key authentication: FAILED - {str(e)}")
    else:
        print("⚠ API Key: Not configured (fallback method)")
    
    return results

def test_phone_numbers():
    """Test if phone numbers are configured"""
    print("\n📞 Phone Number Configuration:")
    
    number_a = os.getenv('TWILIO_NUMBER_A')
    number_b = os.getenv('TWILIO_NUMBER_B')
    
    if number_a:
        print(f"✓ Number A: {number_a}")
    else:
        print("✗ Number A: Not configured")
    
    if number_b:
        print(f"✓ Number B: {number_b}")
    else:
        print("✗ Number B: Not configured")
    
    if not number_a and not number_b:
        print("⚠ Warning: No phone numbers configured. Calls will not work.")

def print_summary(results):
    """Print a summary of the test results"""
    print("\n" + "="*50)
    print("📋 AUTHENTICATION TEST SUMMARY")
    print("="*50)
    
    if results['account_sid'] and (results['api_key'] or results['auth_token']):
        print("✅ SETUP READY: Your Twilio configuration is valid!")
        
        if results['auth_token'] and results['auth_token_client']:
            print("   • Primary: Auth Token authentication")
        elif results['api_key'] and results['api_key_client']:
            print("   • Primary: API Key authentication")
        
        if results['auth_token'] and results['api_key'] and results['auth_token_client'] and results['api_key_client']:
            print("   • Fallback: Both methods available")
        elif results['auth_token'] and results['api_key']:
            print("   • Fallback: Partial (one method failed)")
    
    else:
        print("❌ SETUP INCOMPLETE: Please fix the following issues:")
        for error in results['errors']:
            print(f"   • {error}")
    
    print("\n🔧 Next Steps:")
    if results['account_sid'] and (results['api_key'] or results['auth_token']):
        print("   1. Run 'python app.py' to start the backend")
        print("   2. In another terminal, run 'npm run dev' in the frontend directory")
        print("   3. Open http://localhost:5173 in your browser")
    else:
        print("   1. Check your .env file configuration")
        print("   2. Verify your Twilio credentials")
        print("   3. Ensure you have the required permissions")
        print("   4. Run this test script again")

def main():
    """Main function"""
    print("🔐 Twilio Authentication Test")
    print("="*30)
    
    # Load environment
    if not load_environment():
        print("\n❌ Cannot proceed without environment configuration")
        sys.exit(1)
    
    # Test credentials
    results = test_credentials()
    
    # Test phone numbers
    test_phone_numbers()
    
    # Print summary
    print_summary(results)
    
    # Exit with appropriate code
    if results['account_sid'] and (results['api_key'] or results['auth_token']):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
