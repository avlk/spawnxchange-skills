# Buyer purchase persistence notes

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