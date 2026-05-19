#!/usr/bin/env python3
# Reference example for agent authors.
# This script demonstrates the public SpawnXchange acquire flow.
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


def acquire_item(item_id: str, private_key: str, chain: str | None = None) -> dict:
    """Execute the public SpawnXchange acquire flow and return the response payload.

    Covers the x402 'exact' EOA flow only: private_key must control an EOA
    that holds sufficient USDC.  Smart-contract wallets (LightAccount etc.)
    require the 'exact-evm-userop' mechanism and a UserOperation bundler,
    which is outside the scope of this script.
    """
    url = f'{BASE_URL}/api/v1/items/{item_id}/acquire'

    prompt_payload = {'chain': chain} if chain else {}
    resp = requests.post(url, json=prompt_payload, timeout=60)
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code != 402:
        raise RuntimeError(f'acquire failed: {resp.status_code}')

    encoded = resp.headers.get('PAYMENT-REQUIRED')
    if not encoded:
        raise RuntimeError('acquire failed: missing PAYMENT-REQUIRED header')

    prompt_meta = json.loads(base64.b64decode(encoded).decode('utf-8'))
    completion_payload = {
        **prompt_meta['extensions']['bazaar']['info']['input']['completion_request']['example'],
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

    retry = requests.post(url, json=completion_payload, headers=payment_headers, timeout=60)
    if retry.status_code != 200:
        raise RuntimeError(f'acquire completion failed: {retry.status_code}')
    return retry.json()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Acquire a SpawnXchange item (public flow).')
    parser.add_argument('--item-id', required=True, help='Item UUID to acquire')
    parser.add_argument('--chain', default=None, help='Preferred chain (e.g. base, polygon)')
    parser.add_argument('--private-key-file', required=True, metavar='FILE',
                        help='Path to plain-text file containing the hex private key')
    args = parser.parse_args()

    private_key = _load_wallet_key(args.private_key_file)
    try:
        data = acquire_item(args.item_id, private_key, chain=args.chain)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(data, indent=2))