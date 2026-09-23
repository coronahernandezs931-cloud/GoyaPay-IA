import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

SID = os.environ.get('TWILIO_ACCOUNT_SID')
TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
trunk_sid = os.environ.get('TWILIO_TRUNK_SID', '')

if not SID or not TOKEN:
    print("❌ Error: Debes configurar TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN en tu archivo .env")
    sys.exit(1)

auth = HTTPBasicAuth(SID, TOKEN)
BASE = f'https://api.twilio.com/2010-04-01/Accounts/{SID}'
TRUNKING = 'https://trunking.twilio.com/v1'

# Step 1: Create SIP Credential List
print("1. Creating SIP Credential List...")
r = requests.post(f'{TRUNKING}/SipCredentialLists', auth=auth, data={
    'FriendlyName': 'Retell Auth',
})
r.raise_for_status()
cred_list_sid = r.json()['sid']
print(f"   Credential List SID: {cred_list_sid}")

r = requests.post(f'{TRUNKING}/SipCredentialLists/{cred_list_sid}/Credentials', auth=auth, data={
    'Username': SID,
    'Password': TOKEN,
})
r.raise_for_status()
print(f"   Added credential")

# Step 2: Configure Termination (outbound)
print("\n2. Configuring Termination (outbound)...")
r = requests.post(f'{TRUNKING}/Trunks/{trunk_sid}/Termination', auth=auth, data={
    'CidrAllowList': '18.98.16.120/30',
    'SipAuthUsername': SID,
    'SipAuthPassword': TOKEN,
})
r.raise_for_status()
print(f"   Termination configured OK")

# Step 3: Configure Origination (inbound → Retell SIP server)
print("\n3. Configuring Origination (inbound → sip:sip.retellai.com)...")
r = requests.post(f'{TRUNKING}/Trunks/{trunk_sid}/Origination', auth=auth, data={
    'FriendlyName': 'Retell Inbound',
    'SipUri': 'sip:sip.retellai.com;transport=tcp',
    'Priority': 1,
    'Weight': 1,
    'Enabled': 'true',
    'SipAuthUsername': SID,
    'SipAuthPassword': TOKEN,
})
r.raise_for_status()
print(f"   Origination configured OK")

# Step 4: Move Phone Number to this trunk
phone_number = os.environ.get('TWILIO_PHONE_NUMBER', '')
if phone_number:
    encoded_phone = requests.utils.quote(phone_number)
    print(f"\n4. Moving {phone_number} to SIP trunk...")
    r = requests.get(f'{BASE}/IncomingPhoneNumbers.json?PhoneNumber={encoded_phone}', auth=auth)
    r.raise_for_status()
    numbers = r.json().get('incoming_phone_numbers', [])
    if numbers:
        num_sid = numbers[0]['sid']
        print(f"   Number SID: {num_sid}")
        
        r = requests.post(f'{BASE}/IncomingPhoneNumbers/{num_sid}.json', auth=auth, data={
            'VoiceUrl': '',
            'SipTrunkSid': trunk_sid,
        })
        r.raise_for_status()
        print(f"   Number moved to trunk!")
    else:
        print("   Number NOT found in Twilio account!")
else:
    print("\n4. Skipping moving phone: TWILIO_PHONE_NUMBER not defined in .env")

print(f"\n=== SETUP COMPLETE ===")
print(f"Trunk: {trunk_sid}")
