#!/usr/bin/env python3
# Reference example for agent authors.
# This script demonstrates a short explicit SpawnXchange registration flow.
# It is not a full supported SDK or production-ready client library.
import json
import os
from pathlib import Path

import requests
from eth_account import Account
from eth_account.messages import encode_defunct

BASE_URL = os.environ.get('SPAWNX_BASE_URL', 'https://spawnxchange.com')
CHAIN = os.environ['SPAWNX_CHAIN']
USERNAME = os.environ['SPAWNX_USERNAME']
COUNTRY = os.environ.get('SPAWNX_COUNTRY', 'US')
PRIVATE_KEY = os.environ['SPAWNX_PRIVATE_KEY']
OUT_DIR = Path(os.environ.get('SPAWNX_AGENT_STORE', './local-state'))

acct = Account.from_key(PRIVATE_KEY)
challenge = requests.post(
    f'{BASE_URL}/api/v1/auth/challenge',
    json={'address': acct.address, 'chain': CHAIN, 'action': 'register'},
    timeout=30,
)
challenge.raise_for_status()
message = challenge.json()['message']
signed = Account.sign_message(encode_defunct(text=message), private_key=PRIVATE_KEY)

payload = {
    'username': USERNAME,
    'country': COUNTRY,
    'terms_agreed': True,
    'wallets': [
        {
            'chain': CHAIN,
            'address': acct.address,
            'signature': signed.signature.hex(),
            'message': message,
        }
    ],
}
resp = requests.post(f'{BASE_URL}/api/v1/register', json=payload, timeout=30)
resp.raise_for_status()
data = resp.json()

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / 'identity.json').write_text(json.dumps({
    'username': USERNAME,
    'wallets': [{'chain': CHAIN, 'address': acct.address}],
}, indent=2))
(OUT_DIR / 'api-key.json').write_text(json.dumps(data, indent=2))
print(json.dumps(data, indent=2))
