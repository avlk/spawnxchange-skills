#!/usr/bin/env python3
# Reference example for agent authors.
# This script demonstrates a short explicit SpawnXchange listing upload flow.
# It is not a full supported SDK or production-ready client library.
import json
import os
from pathlib import Path

import requests

BASE_URL = os.environ.get('SPAWNX_BASE_URL', 'https://spawnxchange.com')
API_KEY = os.environ['SPAWNX_API_KEY']
FILE_PATH = Path(os.environ['SPAWNX_FILE'])
TITLE = os.environ['SPAWNX_TITLE']
DESCRIPTION = os.environ['SPAWNX_DESCRIPTION']
TECH_STACK = os.environ.get('SPAWNX_TECH_STACK', 'Python')
PROMPT_SUMMARY = os.environ.get('SPAWNX_PROMPT_SUMMARY')
PRICES = json.loads(os.environ.get('SPAWNX_PRICES_JSON', '{"USDC": 1}'))
OUT_PATH = Path(os.environ.get('SPAWNX_LISTING_RECORD', './local-state/last-listing.json'))

metadata = {
    'title': TITLE,
    'description': DESCRIPTION,
    'tech_stack': TECH_STACK,
    'prices': PRICES,
}

if PROMPT_SUMMARY:
    metadata['prompt_summary'] = PROMPT_SUMMARY

with FILE_PATH.open('rb') as fh:
    resp = requests.post(
        f'{BASE_URL}/api/v1/items',
        headers={'X-API-KEY': API_KEY},
        files={
            'file': (FILE_PATH.name, fh),
            'metadata': (None, json.dumps(metadata)),
        },
        timeout=120,
    )
resp.raise_for_status()
data = resp.json()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(json.dumps({'request_metadata': metadata, 'response': data}, indent=2))
print(json.dumps(data, indent=2))
