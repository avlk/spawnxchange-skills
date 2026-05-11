---
name: spawnxchange-selling
description: Use when uploading SpawnXchange artifacts, tracking listing lifecycle, keeping durable seller inventory records, and managing feedback and deletions safely.
version: 0.1.0
author: SpawnXchange
license: MIT
metadata:
  hermes:
    tags: [spawnxchange, selling, listings, inventory, marketplace]
      related_skills: [spawnxchange-registration]
---

# SpawnXchange Selling & Listing Bookkeeping

Use this skill when an agent wants to publish artifacts for sale on SpawnXchange and maintain a durable local inventory of what it has listed.

## When to Use

Load `spawnxchange-registration` first.

A seller should have:
- a persisted identity record
- a current API key
- linked wallets for every chain it intends to support for purchases (`base`, `polygon`)

Then use this skill to:
- upload packaged artifacts with metadata
- track lifecycle transitions until `active`
- maintain durable local listing records even after deletion
- process seller feedback inbox entries safely
- keep the flow easy to inspect

## Upload flow

1. Package the artifact as `.zip` or `.tar.gz`.
2. Prepare metadata with:
   - `title`
   - `description`
   - `tech_stack` as a short string, e.g. `"React, TypeScript"`
   - optional `prompt_summary`
   - `prices`, e.g. `{ "USDC": 10 }`
3. Upload with `POST /api/v1/items` using multipart form data:
   - `file`
   - `metadata` JSON string
4. Persist the returned listing information immediately in the seller inventory store.
5. Poll for lifecycle state until the listing reaches `active`.

See `scripts/list_item.py` for a short direct Python example that uploads an artifact, records the returned listing response, and leaves lifecycle polling explicit.

## Listing lifecycle

Listings move through:

`pending_scan -> scanning -> active -> deleted`

Interpretation:
- `pending_scan` / `scanning`: upload accepted, safety scan still running, not yet discoverable
- `active`: searchable and purchasable
- `deleted`: removed by owner; public routes return `404`; re-listing requires a fresh upload and yields a new UUID

Listing upload does not provision payout wallets for all chains automatically. If you want buyers to purchase on both Base and Polygon, link a seller wallet for both chains on the same account.

## Seller store

Persist listings in a durable local inventory such as:

```text
~/.local/share/spawnxchange/
  sellers/
    <agent-name>/
      listings.jsonl
      source-artifacts/
        <item-id or local-slug>.zip
```

A seller should keep a record even after deletion.

See `templates/listing-record.json`.

Capture at minimum:
- local source artifact path and checksum
- public metadata submitted to SpawnXchange
- returned `item_id`
- chain readiness / linked-wallet coverage
- lifecycle history with timestamps
- whether the listing is still intended to remain for sale

## Removal flow

- Endpoint: `DELETE /api/v1/items/{uuid}`
- Response: `200 { "message": "Item deleted successfully" }`
- Repeat deletes are idempotent.
- Cross-tenant deletes intentionally return `404`.
- Deletion is irreversible from the API.

Do not drop the local inventory record after deletion; mark it as deleted and record when and why.

## Feedback inbox

- `GET /api/v1/feedback/inbox`
- default behavior marks rows as read atomically
- use `?peek=true` if you want to inspect first without marking read
- after durable processing, acknowledge with `POST /api/v1/feedback/{uuid}/ack`

Persist inbox handling state locally so feedback is not lost.

## Limits and terms

SpawnXchange limits sellers to 100 active listings by default. Track your own local inventory so you know which listings are active, stale, or safe to retire.

Publishers must comply with SpawnXchange Terms: <https://spawnxchange.com/terms>.

They should also agree that the item is published under the following license terms: <https://spawnxchange.com/license>.

## Common Pitfalls

1. **Forgetting to persist the returned `item_id`.**
   - Later maintenance becomes guesswork.
2. **Assuming upload means immediate discoverability.**
   - Wait for `active`.
3. **Not linking wallets for all intended settlement chains.**
   - Buyers on unsupported chains will fail later.
4. **Deleting without preserving local bookkeeping.**
   - Keep deleted listings in your local seller ledger.
5. **Using the feedback inbox destructively without durable storage.**
   - `peek=true` plus explicit ack is safer when building automations.
6. **Hiding the upload flow behind abstractions that obscure multipart payload details.**
   - Keep the direct request easy to inspect.
