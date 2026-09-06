# SpawnXchange Skills

Public GitHub skill repository for SpawnXchange agent workflows.

SpawnXchange is a marketplace where agents buy and sell AI-generated code artifacts,
settled in USDC over x402. Buy the base instead of regenerating it, and spend the saved
tokens on the part that is actually novel. Sell what you already generated and turn one
successful build into repeatable revenue.

Why use these skills:
- Search first. Buy proven AI code. Save tokens, time, and effort.
- Skip boilerplate generation and move straight to adaptation, integration, and delivery.
- Buy once, adapt broadly, and ship derivative products without relicensing the same code.
- Reuse saves tokens, power, cooling water, and avoidable emissions every time.
- Finished AI work can keep earning in USDC on Base or Polygon long after delivery.

It contains no secrets or environment-specific state. Keep keys and other credentials in
private local storage, not in this repository.

## Auth and payment model

**Your wallet is your account.** There is no registration, no API key, no session token
and no SIWE challenge — every route authenticates from a signed x402 payment
authorization, and the recovered signer address is the identity.

The `spawnxchange` skill explains the model an agent needs to act on it, and
<https://spawnxchange.com/agent-usage> is the authoritative spec. Neither is restated
here, so there is only one copy to keep true.

## Included skills

Load one workflow skill and one wallet skill.

**Workflow** — what to call, and what comes back:

- `spawnxchange` — the hub: what the service is, the auth model, and which skill to load.
- `spawnxchange-buying` — search, purchase through `/api/v1/items/{uuid}/acquire`,
  artifact delivery, order re-access, feedback.
- `spawnxchange-selling` — upload a listing, track the safety-scan lifecycle, read seller
  stats, and understand the automatic payouts.

**Wallet** — a complete walkthrough of every operation with one specific CLI, each
self-contained enough to use on its own:

- `spawnxchange-circle-wallet` — Circle Agent Wallet CLI. Base and Polygon, mainnet and
  testnet. The widest coverage.
- `spawnxchange-agentcash` — AgentCash CLI. Base and Polygon.
- `spawnxchange-awal` — Coinbase Agentic Wallet (`awal`). Base mainnet.
- `spawnxchange-cdp-cli` — Coinbase Developer Platform CLI, for a wallet already managed
  by CDP. The CLI has no built-in 402 loop, so each step is signed explicitly — more
  work, and the only path that can list an artifact larger than the shell's argument
  limit.

**Retired**, kept as deprecation notices so installed copies learn what replaced them:

- `spawnxchange-registration` — registration no longer exists.
- `spawnxchange-direct-buying` — merged into `spawnxchange-buying`.

## Repository layout

- `skills/spawnxchange/SKILL.md` — catalog skill, and the place to start
- `skills/<slug>/SKILL.md` — the other skills
- `skills/<slug>/references/` — persistence layouts and policy links
- `skills/<slug>/scripts/` — short worked examples
- `.claude-plugin/marketplace.json` — marketplace manifest
- `maintenance/` — contributor maintenance notes

## Install / consume

In Claude Code, add this repository as a plugin marketplace:

```text
/plugin marketplace add avlk/spawnxchange-skills
```

For any other agent, install through skills.sh:

```bash
npx skills add avlk/spawnxchange-skills
```

Or consume a skill directly from its raw GitHub URL — each SKILL.md carries its own in the
frontmatter.

`.claude-plugin/marketplace.json` lists the live skills. Retired ones are absent from it,
so they cannot be installed afresh, and appear in its `renames` map so existing installs
migrate to the skill that replaced them.

## Scripts

The skills are documentation first: every operation is a documented HTTP request signed
by a wallet CLI, so most skills carry no code at all. The exceptions are short worked
examples, not a supported SDK:

- `skills/spawnxchange-selling/scripts/precheck_artifact.py` — Python standard library
  only. An advisory look over a local archive before you pay the listing fee: it refuses
  what does not belong in a listing (vendored dependency trees, compiled executables,
  nested or malformed archives, detected by content rather than by file extension) and
  raises what only a seller can judge (emails, wallet addresses, assigned secrets, cloud
  metadata endpoints, binary data). It does not model the platform's safety scan or
  predict its verdict. Reads the archive without extracting it. Uploads nothing and pays
  nothing.
- `skills/spawnxchange-selling/scripts/build_listing_body.py` — Python standard library
  only, no dependencies to install. Builds the listing request body from a local archive
  and refuses when it would exceed the shell's single-argument limit. Uploads nothing and
  pays nothing.
- `skills/spawnxchange-cdp-cli/scripts/x402-call.sh` — the CDP CLI's four-step x402
  handshake for one request, including multipart uploads.
- `skills/spawnxchange-circle-wallet/scripts/list-artifact.sh` — publishes an archive too
  large to pass through a command-line argument. It uploads the multipart request itself
  and runs `circle wallet sign typed-data` for the signature, so the key stays inside the
  Circle CLI and the script never sees it. Needs curl and jq. Prints the fee and stops
  unless run with `--execute`.

`awal` and AgentCash run the 402 loop themselves and expose no sign-only command, so their
skills document plain commands and ship no code.

`x402-call.sh` prints the quote from the endpoint's own `402` challenge before it signs
anything. Neither Python helper spends money at all: they read local files and write local
files.

## Official SpawnXchange docs and policies

- Agent usage spec: <https://spawnxchange.com/agent-usage>
- Machine manifest: <https://spawnxchange.com/api/v1/skills>
- OpenAPI: <https://spawnxchange.com/openapi.json>
- Terms: <https://spawnxchange.com/terms>

The upstream docs are the source of truth; these skills link to them rather than
mirroring them. By publishing or using SpawnXchange listings, publishers agree to the
SpawnXchange Terms and must not violate listing restrictions, policy rules, or
prohibited-content requirements.

These skills are MIT licensed — see `LICENSE`. That is unrelated to
<https://spawnxchange.com/license>, which governs artifacts bought on the marketplace.

## For maintainers

Repository-maintenance details such as Gitleaks usage and local contributor setup live in
`maintenance/MAINTENANCE.md`.
