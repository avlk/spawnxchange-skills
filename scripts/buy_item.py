#!/usr/bin/env python3
# Reference example for agent authors.
# This script demonstrates a short explicit SpawnXchange purchase flow.
# It is not a full supported SDK or production-ready client library.
import json
import os

import requests
from eth_account import Account
from x402 import x402ClientSync
from x402.http.x402_http_client import x402HTTPClientSync
from x402.mechanisms.evm.exact import register_exact_evm_client
from x402.mechanisms.evm.signers import EthAccountSigner

BASE_URL = os.environ.get('SPAWNX_BASE_URL', 'https://spawnxchange.com')
API_KEY = os.environ['SPAWNX_API_KEY']
ITEM_ID = os.environ['SPAWNX_ITEM_ID']
CHAIN = os.environ['SPAWNX_CHAIN']
PRIVATE_KEY = os.environ['SPAWNX_PRIVATE_KEY']

payload = {'item_id': ITEM_ID, 'currency': 'USDC', 'chain': CHAIN}
headers = {'X-API-KEY': API_KEY}

resp = requests.post(f'{BASE_URL}/api/v1/buy', json=payload, headers=headers, timeout=60)
if resp.status_code == 200:
    print(json.dumps(resp.json(), indent=2))
    raise SystemExit(0)
if resp.status_code != 402:
    raise SystemExit(f'buy failed: {resp.status_code} {resp.text}')

account = Account.from_key(PRIVATE_KEY)
signer = EthAccountSigner(account)
xclient = x402ClientSync()
register_exact_evm_client(xclient, signer)
http_client = x402HTTPClientSync(xclient)
payment_headers, _payment_payload = http_client.handle_402_response(dict(resp.headers), resp.content)

retry_headers = {**headers, **payment_headers}
retry = requests.post(f'{BASE_URL}/api/v1/buy', json=payload, headers=retry_headers, timeout=60)
retry.raise_for_status()
print(json.dumps(retry.json(), indent=2))
