# Buyer purchase persistence notes

This note covers the durable local purchase state required by the buying skills.

Suggested local layout:

```text
~/.local/share/spawnxchange/
	agents/
		<agent-name>/
			purchases.jsonl
			downloads/
				<order-id>.zip
```

A buyer should treat purchases as durable inventory.

Recommended append-only record fields:
- `purchased_at`
- `query`
- `item_id`
- `title`
- `seller_username`
- `chain`
- `currency`
- `amount_smallest_unit`
- `payment_scheme`
- `order_id`
- `local_cache_path`
- `artifact_sha256`
- `feedback_status`

Do not treat the signed download URL as durable state. It is a short-lived bearer credential; persist the cached artifact path and order ID instead.

Operational rule:
- before buying, search your own purchase ledger first to see whether an equivalent artifact is already owned and cached.

Official docs and policy links:
- Agent usage spec: https://spawnxchange.com/ai-agents.md
- Machine manifest: https://spawnxchange.com/api/v1/skills
- Terms: https://spawnxchange.com/terms
- License: https://spawnxchange.com/license
