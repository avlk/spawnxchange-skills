#!/usr/bin/env python3
import json
import os

from web3 import Web3

EXPLORER_TX_URLS = {
    'base': 'https://basescan.org/tx/',
    'polygon': 'https://polygonscan.com/tx/',
}

DEFAULT_WITHDRAW_SETTINGS = {
    'rpc_urls': {
        'base': 'https://mainnet.base.org',
        'polygon': 'https://polygon-bor-rpc.publicnode.com',
    },
    'marketplace_contracts': {
        'base': '0x40c815cdeadc163821d2cf784166d7fbb60e1d94',
        'polygon': '0xa54b195a0bfe298b11fc196387a41e3c331a6cbd',
    },
    'token_addresses': {
        'base': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        'polygon': '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359',
    },
}

WITHDRAW_ABI = [
    {
        'type': 'function',
        'name': 'withdraw',
        'stateMutability': 'nonpayable',
        'inputs': [{'name': 'token', 'type': 'address'}],
        'outputs': [],
    }
]


def withdraw_payout(private_key, chain, settings=None):
    if chain not in {'base', 'polygon'}:
        raise ValueError('missing or invalid chain: set SPAWNX_CHAIN=base or SPAWNX_CHAIN=polygon')

    if settings is None:
        settings = DEFAULT_WITHDRAW_SETTINGS

    rpc_urls = settings['rpc_urls']
    marketplace_contracts = settings['marketplace_contracts']
    token_addresses = settings['token_addresses']

    w3 = Web3(Web3.HTTPProvider(rpc_urls[chain]))
    account = w3.eth.account.from_key(private_key)
    contract_address = Web3.to_checksum_address(marketplace_contracts[chain])
    token_address = Web3.to_checksum_address(token_addresses[chain])
    contract = w3.eth.contract(address=contract_address, abi=WITHDRAW_ABI)

    tx = contract.functions.withdraw(token_address).build_transaction(
        {
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': w3.eth.chain_id,
            'gasPrice': w3.eth.gas_price,
        }
    )
    tx['gas'] = w3.eth.estimate_gas(tx)

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    return {
        'chain': chain,
        'wallet_address': account.address,
        'marketplace_contract': contract_address,
        'token_address': token_address,
        'transaction_hash': tx_hash.hex(),
        'transaction_url': f'{EXPLORER_TX_URLS[chain]}{tx_hash.hex()}',
        'receipt_status': int(receipt.status),
        'block_number': int(receipt.blockNumber),
    }


def main():
    private_key = os.environ['SPAWNX_PRIVATE_KEY']
    chain = os.environ.get('SPAWNX_CHAIN', '').strip().lower()

    try:
        result = withdraw_payout(private_key, chain)
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()