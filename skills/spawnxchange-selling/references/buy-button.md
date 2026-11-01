# Buy with your agent block

A block a seller pastes into a README or web page so that other people's agents can buy
the listing directly. It works with the listing's id and the public API as they are.

```bash
python3 scripts/buy_snippet.py --item "<item_id>"                        # README (markdown)
python3 scripts/buy_snippet.py --item "<item_id>" --format html          # website embed
python3 scripts/buy_snippet.py --item "<item_id>" --format page          # standalone chooser page
python3 scripts/buy_snippet.py --item "<item_id>" --chooser-url "<https page>"   # README badge target (md only)
```

The script reads `GET https://spawnxchange.com/api/v1/items/<item_id>`, prints to stdout,
and writes, signs and pays nothing. It exits non-zero, saying why, when the item is not
listed or its status is not `active`: run it after the safety scan has passed.

## The three outputs

All three are generated from one table of ways to buy in `buy_snippet.py`, so they cannot
drift.

- **`html`**: a large "Buy with your agent · <price> USDC" button that opens a chooser in a
  dialog. Inline CSS and a small inline script; no external requests, no tracking. Paste it
  into any page that allows scripts.
- **`md`**: GitHub strips scripts and styles, so the button is a large static shields.io
  badge. It links to `--chooser-url` when given, otherwise to
  `https://spawnxchange.com/c/buy-badge`, which lands on the SpawnXchange home page: a
  badge cannot open a chooser on GitHub, so until SpawnXchange hosts one, host your own
  `--format page` output and pass its address as `--chooser-url`. Under it: one facts line and a collapsible
  "Ways to buy" holding the same one-liners.
- **`page`**: the chooser as a standalone HTML page, the thing a badge should link to.

## The chooser

One compact line at the top: title, price, chains, "Safety-scanned before listing", and the
Licence and Terms links. Then a short list of methods; each shows one copyable line (or one
link) and a sentence, with a setup link where the wallet needs one:

- **Any skills-capable agent** (Claude Code, OpenClaw): one line to paste into the agent. It
  installs the buying skill, then says: "I'd like to buy SpawnXchange item <ID>. Show me the
  price and terms, and ask me before paying."
- **AgentCash**, **Coinbase Agentic Wallet (awal)**, **Circle**: the wallet's own purchase
  command for this item, capped at the price. awal appears only for items sold on Base. AgentCash and awal run as `npx <pkg>@<pin>`,
  pinned to the versions in `PINS`; `lint.sh` checks the script's pins against the generator.
- **Poncho**: an "Open in Poncho" link that opens Poncho with the same request as the
  opening prompt.

The CDP CLI has no one-line pay command (only `cdp util x402 build/encode`), so it has no
entry of its own; the skills option covers it through `spawnxchange-cdp-cli`.

Paste the output as printed. The price is the price when you ran the script; run it again if
the price changes.
