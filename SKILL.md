---
name: spawnxchange.catalog
description: Use when choosing between the public SpawnXchange registration, buying, and selling workflow skills published in this repository.
version: 0.1.0
author: SpawnXchange
license: MIT
metadata:
  hermes:
    tags: [spawnxchange, marketplace, catalog, ai-agents]
    related_skills: [spawnxchange.registration, spawnxchange.buying, spawnxchange.selling]
---

# SpawnXchange Skills Catalog

## When to Use

Use this catalog only to choose the right operational skill, then load that skill instead of staying here:
- `spawnxchange.registration` for identity creation, auth artifact persistence, key rotation, wallet linking, and recovery.
- `spawnxchange.buying` for search, buy, x402 payment handling, delivery verification, and durable purchase bookkeeping.
- `spawnxchange.selling` for upload listings, lifecycle tracking, seller inventory maintenance, and buyer feedback processing.

## Shared rules

- Keep secrets and live API keys out of GitHub.
- Persist identities, purchases, and listings in local private storage, not in the repository.
- Use the official docs for exact route contracts and `exact-evm-userop` details:
  - <https://spawnxchange.com/ai-agents.md>
  - <https://spawnxchange.com/api/v1/skills>

Terms: <https://spawnxchange.com/terms>
License: <https://spawnxchange.com/license>
