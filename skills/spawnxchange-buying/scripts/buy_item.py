#!/usr/bin/env python3
# Reference example for agent authors.
# This script demonstrates a short explicit SpawnXchange purchase flow.
# It is not a full supported SDK or production-ready client library.
import argparse
import base64
import json
from pathlib import Path

import requests
from eth_account import Account
from x402 import x402ClientSync
from x402.http.x402_http_client import x402HTTPClientSync
from x402.mechanisms.evm.exact import register_exact_evm_client
from x402.mechanisms.evm.signers import EthAccountSigner

BASE_URL = 'https://spawnxchange.com'


def _load_wallet_key(path: str) -> str:
    """Read a plain-text hex private key file, stripping whitespace."""
    return Path(path).read_text().strip()


def _load_api_key(path: str) -> str:
    """Read api_key field from a JSON file (e.g. saved by register_agent.py)."""
    data = json.loads(Path(path).read_text())
    key = data.get('api_key')
    if not key:
        raise RuntimeError(f'api_key field not found in {path}')
    return key


def buy_item(item_id: str, private_key: str, api_key: str, chain: str | None = None) -> dict:
    """Execute the authenticated SpawnXchange buy flow and return the response payload.

    Covers the x402 'exact' EOA flow only: private_key must control an EOA
    that holds sufficient USDC.  Smart-contract wallets (LightAccount etc.)
    require the 'exact-evm-userop' mechanism and a UserOperation bundler,
    which is outside the scope of this script.
    """
    headers = {'X-API-KEY': api_key}

    prompt_payload: dict = {'item_id': item_id}
    if chain:
        prompt_payload['chain'] = chain

    resp = requests.post(
        f'{BASE_URL}/api/v1/buy',
        json=prompt_payload,
        headers=headers,
        timeout=60,
    )
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code != 402:
        raise RuntimeError(f'buy failed: {resp.status_code}')

    encoded = resp.headers.get('PAYMENT-REQUIRED')
    if not encoded:
        raise RuntimeError('buy failed: missing PAYMENT-REQUIRED header')

    prompt_meta = json.loads(base64.b64decode(encoded).decode('utf-8'))
    completion_payload = {
        **prompt_meta['extensions']['spawnxchange']['input']['completion_request']['example'],
        'item_id': item_id,
        'policy_accepted': True,
        'license_accepted': True,
        **({'chain': chain} if chain else {}),
    }

    account = Account.from_key(private_key)
    signer = EthAccountSigner(account)
    xclient = x402ClientSync()
    register_exact_evm_client(xclient, signer)
    http_client = x402HTTPClientSync(xclient)
    payment_headers, _ = http_client.handle_402_response(dict(resp.headers), resp.content)

    retry_headers = {**headers, **payment_headers}
    retry = requests.post(
        f'{BASE_URL}/api/v1/buy',
        json=completion_payload,
        headers=retry_headers,
        timeout=60,
    )
    if retry.status_code != 200:
        raise RuntimeError(f'buy completion failed: {retry.status_code}')
    return retry.json()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Buy a SpawnXchange item (authenticated flow).')
    parser.add_argument('--item-id', required=True, help='Item UUID to purchase')
    parser.add_argument('--chain', default=None, help='Preferred chain (e.g. base, polygon)')
    parser.add_argument('--private-key-file', required=True, metavar='FILE',
                        help='Path to plain-text file containing the hex private key')
    parser.add_argument('--api-key-file', required=True, metavar='FILE',
                        help='Path to api-key.json written by register_agent.py')
    args = parser.parse_args()

    private_key = _load_wallet_key(args.private_key_file)
    try:
        api_key = _load_api_key(args.api_key_file)
        data = buy_item(args.item_id, private_key, api_key, chain=args.chain)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(data, indent=2))
