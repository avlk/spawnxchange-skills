#!/usr/bin/env python3
# Reference example for agent authors.
# This script demonstrates the public SpawnXchange acquire flow.
# It is not a full supported SDK or production-ready client library.
import base64
import json
import os

import requests
from eth_account import Account
from x402 import x402ClientSync
from x402.http.x402_http_client import x402HTTPClientSync
from x402.mechanisms.evm.exact import register_exact_evm_client
from x402.mechanisms.evm.signers import EthAccountSigner

BASE_URL = os.environ.get('SPAWNX_BASE_URL', 'https://spawnxchange.com')
ITEM_ID = os.environ['SPAWNX_ITEM_ID']
CHAIN = os.environ.get('SPAWNX_CHAIN')
PRIVATE_KEY = os.environ['SPAWNX_PRIVATE_KEY']

url = f'{BASE_URL}/api/v1/items/{ITEM_ID}/acquire'


prompt_payload = {'chain': CHAIN} if CHAIN else {}

resp = requests.post(url, json=prompt_payload, timeout=60)
if resp.status_code == 200:
    print(json.dumps(resp.json(), indent=2))
    raise SystemExit(0)
if resp.status_code != 402:
    raise SystemExit(f'acquire failed: {resp.status_code}')

encoded = resp.headers.get('PAYMENT-REQUIRED')
if not encoded:
    raise SystemExit('acquire failed: missing PAYMENT-REQUIRED header')

prompt_meta = json.loads(base64.b64decode(encoded).decode('utf-8'))
completion_payload = {
    **prompt_meta['extensions']['bazaar']['info']['input']['completion_request']['example'],
    'policy_accepted': True,
    'license_accepted': True,
    **({'chain': CHAIN} if CHAIN else {}),
}

account = Account.from_key(PRIVATE_KEY)
signer = EthAccountSigner(account)
xclient = x402ClientSync()
register_exact_evm_client(xclient, signer)
http_client = x402HTTPClientSync(xclient)
payment_headers, _ = http_client.handle_402_response(dict(resp.headers), resp.content)

retry = requests.post(url, json=completion_payload, headers=payment_headers, timeout=60)
if retry.status_code != 200:
    raise SystemExit(f'acquire completion failed: {retry.status_code}')
print(json.dumps(retry.json(), indent=2))