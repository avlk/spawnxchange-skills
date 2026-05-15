#!/usr/bin/env python3
import json
import os
from decimal import Decimal

import requests


def format_amount(amount_text):
    amount = Decimal(str(amount_text or '0'))
    return format(amount.normalize(), 'f') if amount else '0'


def get_pending_payouts(api_key, base_url='https://spawnxchange.com'):
    resp = requests.get(
        f'{base_url}/api/v1/seller/payouts',
        headers={'X-API-KEY': api_key},
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f'payout lookup failed: {resp.status_code} {resp.text[:500]}'
        )

    body = resp.json()
    chain_amounts = {}
    errors = {}

    for payout in body.get('payouts', []):
        if payout.get('currency') != 'USDC':
            continue
        chain = payout.get('chain')
        if not chain:
            continue
        if payout.get('status') == 'ok':
            chain_amounts[chain] = format_amount(payout.get('amount'))
        else:
            chain_amounts[chain] = None
            errors[chain] = payout.get('status', 'unknown_error')

    known_amounts = [Decimal(value) for value in chain_amounts.values() if value is not None]
    data = {
        'source': 'spawnxchange_api',
        'currency': 'USDC',
        'pending': chain_amounts,
        'total_pending': format(sum(known_amounts, Decimal('0')).normalize(), 'f') if known_amounts else '0',
    }
    if errors:
        data['errors'] = errors
    return data


def main():
    base_url = os.environ.get('SPAWNX_BASE_URL', 'https://spawnxchange.com')
    api_key = os.environ['SPAWNX_API_KEY']
    try:
        data = get_pending_payouts(api_key, base_url=base_url)
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()