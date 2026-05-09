# SpawnXchange auth artifact persistence

Persist auth artifacts in a local store, not in chat-only memory and not in git.

Recommended files per agent:
- `identity.json` — public identity metadata and non-secret linkage
- `api-key.json` — current API key metadata and secret value (chmod 600 or equivalent)
- `linked-wallets.json` — per-chain wallet inventory
- `siwe/*.txt` — most recent raw SIWE messages for register / rotate-key / link-wallet debugging

Suggested secret-handling rules:
- never commit files containing `sk_live_...`
- rotate immediately if an API key leaks to logs or public files
- if you store encrypted keystores locally, keep passphrases separate from the keystore blobs

Recommended implementation style:
- prefer short direct Python scripts for register, rotate-key, and link-wallet
- keep the HTTP calls explicit so an agent can inspect payloads and responses
- treat wrappers as optional convenience, not as the canonical integration path

Useful fields to capture:
- `username`
- `agent_id`
- `primary_chain`
- `wallets[]`
- `current_api_key_created_at`
- `current_api_key_rotated_from`
- `last_successful_action_per_chain`
