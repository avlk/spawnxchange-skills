#!/usr/bin/env python3
import json
import os
from decimal import Decimal

from web3 import Web3

DEFAULT_BASE_RPC_URL = 'https://mainnet.base.org'
DEFAULT_POLYGON_RPC_URL = 'https://polygon-bor-rpc.publicnode.com'
DEFAULT_MARKETPLACE_CONTRACT_BASE = '0x40c815cdeadc163821d2cf784166d7fbb60e1d94'
DEFAULT_MARKETPLACE_CONTRACT_POLYGON = '0xa54b195a0bfe298b11fc196387a41e3c331a6cbd'
DEFAULT_USDC_ADDRESS_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
DEFAULT_USDC_ADDRESS_POLYGON = '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'

MARKETPLACE_ABI = [
    {
        'type': 'function',
        'name': 'balances',
        'stateMutability': 'view',
        'inputs': [
            {'name': 'walletAddress', 'type': 'address'},
            {'name': 'tokenAddress', 'type': 'address'},
        ],
        'outputs': [{'name': 'amount', 'type': 'uint256'}],
    }
]


def format_amount(amount_raw):
    amount = Decimal(amount_raw) / Decimal(10**6)
    return format(amount.normalize(), 'f') if amount_raw else '0'


def get_pending_payouts(wallet_address, config=None):
    wallet_address = Web3.to_checksum_address(wallet_address)
    if config is None:
        config = {
            'base': {
                'rpc_url': os.environ.get('SPAWNX_BASE_RPC_URL', DEFAULT_BASE_RPC_URL),
                'marketplace_contract': os.environ.get(
                    'SPAWNX_MARKETPLACE_CONTRACT_BASE',
                    DEFAULT_MARKETPLACE_CONTRACT_BASE,
                ),
                'token_address': os.environ.get(
                    'SPAWNX_USDC_ADDRESS_BASE',
                    DEFAULT_USDC_ADDRESS_BASE,
                ),
            },
            'polygon': {
                'rpc_url': os.environ.get(
                    'SPAWNX_POLYGON_RPC_URL',
                    DEFAULT_POLYGON_RPC_URL,
                ),
                'marketplace_contract': os.environ.get(
                    'SPAWNX_MARKETPLACE_CONTRACT_POLYGON',
                    DEFAULT_MARKETPLACE_CONTRACT_POLYGON,
                ),
                'token_address': os.environ.get(
                    'SPAWNX_USDC_ADDRESS_POLYGON',
                    DEFAULT_USDC_ADDRESS_POLYGON,
                ),
            },
        }

    chain_amounts = {}
    errors = {}

    for chain, cfg in config.items():
        try:
            marketplace_contract = Web3.to_checksum_address(cfg['marketplace_contract'])
            token_address = Web3.to_checksum_address(cfg['token_address'])
            w3 = Web3(Web3.HTTPProvider(cfg['rpc_url']))
            contract = w3.eth.contract(address=marketplace_contract, abi=MARKETPLACE_ABI)
            amount_raw = contract.functions.balances(wallet_address, token_address).call()
            chain_amounts[chain] = format_amount(amount_raw)
        except Exception as exc:
            chain_amounts[chain] = None
            errors[chain] = str(exc)[:200]

    known_amounts = [Decimal(value) for value in chain_amounts.values() if value is not None]
    data = {
        'source': 'onchain',
        'wallet_address': wallet_address,
        'currency': 'USDC',
        'pending': chain_amounts,
        'total_pending': format(sum(known_amounts, Decimal('0')).normalize(), 'f') if known_amounts else '0',
    }
    if errors:
        data['errors'] = errors
    return data


def main():
    wallet_address = os.environ.get('SPAWNX_WALLET_ADDRESS')
    if not wallet_address:
        raise SystemExit('missing wallet address: set SPAWNX_WALLET_ADDRESS')

    try:
        data = get_pending_payouts(wallet_address)
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()