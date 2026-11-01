#!/usr/bin/env python3
"""Print a "Buy with your agent" block for one live SpawnXchange listing.

Standard library only. One public, unauthenticated GET to
https://spawnxchange.com/api/v1/items/<id>; no wallet, no signature, no payment,
no environment reads, and nothing written to disk -- the block goes to stdout so
the seller can paste it into a README or a web page.

The block addresses the human who reads the README, never an agent. It carries
the price, the chains, a badge and the exact purchase command for each wallet CLI
the SpawnXchange wallet skills cover, each capped at the item's price.
"""

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from urllib.parse import quote, urlsplit

BASE_URL = "https://spawnxchange.com"
BADGE_CAMPAIGN_URL = BASE_URL + "/c/buy-badge"
BADGE_COLOR = "0052FF"
SAFETY_LINE = "Safety-scanned before listing"
# Pinned like every npx the skills run, so a pasted command cannot change after review.
# Keep in step with PINS in maintenance/generate-wallet-skills.py (lint checks it).
SKILLS_PIN = "skills@1.5.24"
AGENTCASH_PIN = "agentcash@0.17.1"
AWAL_PIN = "awal@2.12.1"
INSTALL_COMMAND = f"npx {SKILLS_PIN} add avlk/spawnxchange-skills --skill spawnxchange-buying --yes"
PONCHO_URL = "https://tryponcho.com/"
BODY = '{"policy_accepted":true,"license_accepted":true}'

ITEM_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)
MAX_PRICE_USDC = Decimal(1_000_000)  # sanity bound only; the marketplace enforces its own band
MAX_TITLE_CHARS = 80
TIMEOUT_SECONDS = 15

# Marketplace chain name -> (display name, agentcash network, circle --chain).
CHAINS = {
    "base": ("Base", "base", "BASE"),
    "polygon": ("Polygon", "polygon", "MATIC"),
}


class SnippetError(Exception):
    """Raised for anything that stops a block from being produced."""


def parse_chooser_url(value):
    """Return a safe page URL for the badge to link to, or raise.

    https anywhere; plain http only for a loopback address, so a demo can run
    locally. No whitespace, quotes or angle brackets, so it fits any attribute.
    """
    message = "--chooser-url must be an https URL (http only for localhost)."
    try:
        parts = urlsplit(value)
        hostname = parts.hostname
    except ValueError:
        raise SnippetError(message)
    loopback = hostname in ("localhost", "127.0.0.1", "::1")
    ok_scheme = parts.scheme == "https" or (parts.scheme == "http" and loopback)
    if not ok_scheme or not hostname or re.search(r"[\s\"'<>`()\\]", value):
        raise SnippetError(message)
    return value


def parse_item_id(value):
    """Return the lower-cased UUID, or raise. Keeps the id safe to put in a URL."""
    if not ITEM_ID_RE.fullmatch(value):
        raise SnippetError("--item must be an item id (a UUID), as returned by search.")
    return value.lower()


def fetch_item(item_id):
    """GET the public item record and return it as a dict."""
    url = f"{BASE_URL}/api/v1/items/{quote(item_id)}"
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "spawnxchange-buy-snippet/1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read(1_000_000).decode("utf-8"))
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise SnippetError(
                f"Item {item_id} is not listed. It may still be scanning, may have been "
                "rejected, or may have been removed. Check its status as the seller, and "
                "run this again once it is active."
            )
        raise SnippetError(f"SpawnXchange answered HTTP {err.code} for item {item_id}.")
    except (urllib.error.URLError, TimeoutError, ValueError) as err:
        raise SnippetError(f"Could not read item {item_id}: {err}")
    if not isinstance(payload, dict):
        raise SnippetError("Unexpected response shape from the item endpoint.")
    return payload


def summarize(item_id, payload):
    """Validate a payload and return plain data: id, title, price (Decimal), chains."""
    if payload.get("status") != "active":
        raise SnippetError(
            f"Item {item_id} has status {payload.get('status')!r}, not 'active'. "
            "A block is only produced for a live listing; run this again once the "
            "safety scan has passed."
        )
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise SnippetError("The item record has no metadata.")
    prices = metadata.get("prices")
    raw = prices.get("USDC") if isinstance(prices, dict) else None
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise SnippetError("The item has no USDC price.")
    try:
        price = Decimal(str(raw))
    except InvalidOperation:
        raise SnippetError("The item's USDC price is not a number.")
    if not price.is_finite() or not 0 < price <= MAX_PRICE_USDC:
        raise SnippetError("The item's USDC price is not a usable positive number.")
    listed = payload.get("available_chains")
    if not isinstance(listed, list):
        raise SnippetError("The item lists no chains.")
    chains = [c for c in listed if isinstance(c, str) and c in CHAINS]
    if not chains:
        raise SnippetError("The item lists no chain this script knows (base, polygon).")
    title = " ".join(str(metadata.get("title") or "").split())[:MAX_TITLE_CHARS]
    return {"id": item_id, "title": title, "price": price, "chains": chains}


def plain(amount):
    """Format a Decimal without exponent or trailing zeros: 1.25, 10."""
    return format(amount.normalize(), "f")


def atomic(amount):
    """USDC has 6 decimals; awal wants whole base units.

    Rounds up, so the spend cap is never below the price.
    """
    return str(int((amount * 1_000_000).to_integral_value(rounding=ROUND_CEILING)))


# ---- the single table of ways to buy ---------------------------------------
# Every output (md, html, page) is generated from WAYS, so they cannot drift.
# Each way is: (key, name, kind, value(summary), sentence, (link label, link url) or None)
# kind "copy": value is one line to copy. kind "link": value is a URL to open.

def acquire_url(summary):
    return f"{BASE_URL}/api/v1/items/{summary['id']}/acquire"


def ask_sentence(s):
    """What the person says to their agent: a request that carries the consent step."""
    return (f"I'd like to buy SpawnXchange item {s['id']}. Show me the price and terms, "
            "and ask me before paying.")


def way_skill(s):
    return f"Install the SpawnXchange buying skill ({INSTALL_COMMAND}), then: {ask_sentence(s)}"


def way_agentcash(s):
    return (f"npx {AGENTCASH_PIN} fetch {acquire_url(s)} -m POST "
            f"-H 'Content-Type: application/json' -b '{BODY}' "
            f"--max-amount {plain(s['price'])}")


def way_poncho(s):
    # Poncho's start page reads ?p= as the opening prompt, logged in or not.
    return f"{PONCHO_URL}?p={quote(ask_sentence(s))}"


def way_awal(s):
    return (f"npx {AWAL_PIN} x402 pay {acquire_url(s)} -X POST -d '{BODY}' "
            f"-h '{{\"Content-Type\":\"application/json\"}}' --max-amount {atomic(s['price'])}")


def way_circle(s):
    chain = CHAINS[s["chains"][0]][2]
    return (f"circle services pay {acquire_url(s)} --address '<your-wallet-address>' "
            f"--chain {chain} -X POST -H 'Content-Type: application/json' -d '{BODY}' "
            f"--max-amount {plain(s['price'])}")


WAYS = [
    ("skill", "Claude Code, OpenClaw or any skills-capable agent", "copy", way_skill,
     "Paste into your agent; our skill has it show you the price and terms and ask you before it pays.",
     None),
    ("agentcash", "AgentCash", "copy", way_agentcash,
     "Run in a terminal with a funded AgentCash wallet; it pays at most the price.",
     ("AgentCash setup", "https://agentcash.dev/docs")),
    ("poncho", "Poncho", "link", way_poncho,
     "Opens Poncho with a request to buy this item.", None),
    ("awal", "Coinbase Agentic Wallet (awal)", "copy", way_awal,
     "Run in a terminal once you are signed in to awal; it pays at most the price.",
     ("awal setup", "https://docs.cdp.coinbase.com/agentic-wallet/cli/welcome")),
    ("circle", "Circle Agent Wallet", "copy", way_circle,
     "Run in a terminal with the Circle CLI and a funded wallet; it pays at most the price.",
     ("Circle wallet setup", "https://developers.circle.com/agent-stack/agent-wallets")),
]


# awal pays on Base only; a way is offered only when this says it can pay for the item.
AVAILABLE = {"awal": lambda summary: "base" in summary["chains"]}


def ways_for(summary):
    return [w for w in WAYS if AVAILABLE.get(w[0], lambda _s: True)(summary)]


def chain_names(summary):
    return ", ".join(CHAINS[c][0] for c in summary["chains"])


def button_label(summary):
    return f"Buy with your agent \u00b7 {plain(summary['price'])} USDC"


def badge_url(summary):
    """A large static shields.io badge (for-the-badge style) carrying the price."""
    text = quote(button_label(summary).replace("-", "--"))
    return f"https://img.shields.io/badge/{text}-{BADGE_COLOR}?style=for-the-badge"


def md_escape(text):
    """Neutralise markdown and HTML metacharacters in seller-supplied text."""
    return re.sub(r"([\\`*_{}\[\]<>()#+!|~&-])", r"\\\1", text)


def facts_text(summary, title):
    return (f"{title} \u00b7 {plain(summary['price'])} USDC \u00b7 {chain_names(summary)} "
            f"\u00b7 {SAFETY_LINE}")


def render_markdown(summary, chooser_url=None):
    title = md_escape(summary["title"]) or "This listing"
    target = chooser_url or BADGE_CAMPAIGN_URL
    ways = []
    for key, name, kind, value, sentence, link in ways_for(summary):
        text = value(summary)
        extra = f" [{link[0]}]({link[1]})" if link else ""
        # The skill line is a sentence for the agent, not a shell command.
        fence = "text" if key == "skill" else "bash"
        body = f"[Open in {name}]({text})" if kind == "link" else f"```{fence}\n{text}\n```"
        ways.append(f"**{name}.** {sentence.format(id=summary['id'])}{extra}\n\n{body}")
    listing = "\n\n".join(ways)
    return f"""[![{button_label(summary)}]({badge_url(summary)})]({target})

**{title}** \u00b7 {plain(summary['price'])} USDC \u00b7 {chain_names(summary)} \u00b7 {SAFETY_LINE} \u00b7 Buying accepts the [Licence]({BASE_URL}/license) and [Terms]({BASE_URL}/terms)

<details>
<summary>Ways to buy</summary>

{listing}

</details>
"""


# ---- chooser (HTML) ---------------------------------------------------------

CSS = """
.sxbuy{--bg:#fff;--fg:#1f2328;--mut:#59636e;--bd:#d1d9e0;--code:#f6f8fa;--lnk:#0969da;--sel:#0052ff;font:15px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--fg)}
@media(prefers-color-scheme:dark){.sxbuy{--bg:#0d1117;--fg:#e6edf3;--mut:#9198a1;--bd:#3d444d;--code:#151b23;--lnk:#4493f8;--sel:#3b78ff}}
.sxbuy,.sxbuy *{box-sizing:border-box}
.sxbuy-btn{display:inline-block;cursor:pointer;border:0;border-radius:8px;background:#0052ff;color:#fff;font:700 17px/1 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;padding:16px 26px;box-shadow:0 2px 0 rgba(0,0,0,.25),0 6px 16px rgba(0,82,255,.35);letter-spacing:.01em}
.sxbuy-btn:hover{background:#1a66ff}.sxbuy-btn:focus-visible{outline:3px solid #8ab4ff;outline-offset:2px}
dialog.sxbuy{border:1px solid var(--bd);border-radius:12px;padding:0;background:var(--bg);color:var(--fg);width:min(640px,calc(100vw - 24px));max-height:calc(100vh - 32px);overflow:auto}
dialog.sxbuy::backdrop{background:rgba(0,0,0,.55)}
.sxbuy-in{padding:20px 24px 24px}
.sxbuy-top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.sxbuy h3{margin:0 0 4px;font-size:20px}
.sxbuy p{margin:0 0 8px}.sxbuy .sxbuy-facts{color:var(--mut);font-size:14px;margin:0 0 14px}
.sxbuy a{color:var(--lnk)}
.sxbuy-x{cursor:pointer;border:1px solid var(--bd);background:var(--bg);color:var(--fg);border-radius:6px;font-size:18px;line-height:1;padding:6px 10px}
.sxbuy-tabs{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.sxbuy-tab{cursor:pointer;border:1px solid var(--bd);background:var(--bg);color:var(--fg);border-radius:999px;font:600 13px/1 -apple-system,"Segoe UI",sans-serif;padding:9px 13px}
.sxbuy-tab[aria-selected=true]{background:var(--sel);border-color:var(--sel);color:#fff}
.sxbuy-js .sxbuy-panel{display:none}.sxbuy-js .sxbuy-panel.on{display:block}
.sxbuy-chooser:not(.sxbuy-js) .sxbuy-tabs{display:none}
.sxbuy-panel{border-top:1px solid var(--bd);padding-top:12px}
.sxbuy-panel h4{margin:0 0 2px;font-size:15px}
.sxbuy-panel>p{color:var(--mut);font-size:14px}
.sxbuy-code{position:relative;margin:0 0 4px}
.sxbuy-code pre{margin:0;background:var(--code);border-radius:8px;padding:12px 76px 12px 12px;overflow:auto;font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-all}
.sxbuy-code code{font:inherit}
.sxbuy-cp{position:absolute;top:8px;right:8px;cursor:pointer;border:1px solid var(--bd);background:var(--bg);color:var(--fg);border-radius:6px;font:600 12px/1 -apple-system,"Segoe UI",sans-serif;padding:6px 10px}
.sxbuy a.sxbuy-go{display:inline-block;background:#0052ff;color:#fff;text-decoration:none;font-weight:700;border-radius:8px;padding:12px 18px}
"""

SCRIPT = """(function(){
function pick(r,i){var t=r.querySelectorAll('.sxbuy-tab'),p=r.querySelectorAll('.sxbuy-panel');
for(var k=0;k<p.length;k++){var on=k==i;p[k].classList.toggle('on',on);t[k].setAttribute('aria-selected',on?'true':'false')}}
function init(){var c=document.querySelectorAll('.sxbuy-chooser:not(.sxbuy-js)');
for(var i=0;i<c.length;i++){c[i].classList.add('sxbuy-js');pick(c[i],0)}}
function fb(t,d){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();try{document.execCommand('copy');d()}catch(e){}document.body.removeChild(a)}
function cp(t,b){var d=function(){var o=b.textContent;b.textContent='Copied';setTimeout(function(){b.textContent=o},1500)};
if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(d,function(){fb(t,d)})}else{fb(t,d)}}
init();
if(window.__sxbuy)return;window.__sxbuy=1;
document.addEventListener('click',function(e){var n=e.target;
if(n.tagName==='DIALOG'&&n.className.indexOf('sxbuy')>-1){n.close?n.close():n.removeAttribute('open');return}
var t=n.closest?n.closest('[data-sxbuy]'):null;if(!t)return;var k=t.getAttribute('data-sxbuy');
if(k==='open'){var d=document.getElementById(t.getAttribute('data-for'));if(d){d.showModal?d.showModal():d.setAttribute('open','')}}
else if(k==='close'){var g=t.closest('dialog');if(g){g.close?g.close():g.removeAttribute('open')}}
else if(k==='tab'){pick(t.closest('.sxbuy-chooser'),+t.getAttribute('data-i'))}
else if(k==='copy'){cp(t.parentNode.querySelector('pre').textContent,t)}})})();"""


def panel_html(summary, way):
    key, name, kind, value, sentence, link = way
    text = value(summary)
    extra = (f' <a href="{html.escape(link[1])}">{html.escape(link[0])}</a>' if link else "")
    if kind == "link":
        body = (f'<p><a class="sxbuy-go" href="{html.escape(text)}" target="_blank" '
                f'rel="noopener noreferrer">Open in {html.escape(name)}</a></p>')
    else:
        body = (f'<div class="sxbuy-code"><pre><code>{html.escape(text)}</code></pre>'
                '<button type="button" class="sxbuy-cp" data-sxbuy="copy">Copy</button></div>')
    return (f'<div class="sxbuy-panel" role="tabpanel" id="sxbuy-{summary["id"]}-{key}"><p>'
            f'{html.escape(sentence.format(id=summary["id"]))}{extra}</p>{body}</div>')


def chooser_body(summary, close_button):
    """Facts once on top, then one tab per way to buy; each shows one line or link."""
    title = html.escape(summary["title"]) or "This listing"
    close = ('<button type="button" class="sxbuy-x" data-sxbuy="close" aria-label="Close">'
             '&times;</button>' if close_button else "")
    ways = ways_for(summary)
    tabs = "".join(
        f'<button type="button" class="sxbuy-tab" role="tab" data-sxbuy="tab" data-i="{i}" '
        f'aria-controls="sxbuy-{summary["id"]}-{w[0]}" aria-selected="false">'
        f'{html.escape(w[1])}</button>' for i, w in enumerate(ways))
    panels = "".join(panel_html(summary, w) for w in ways)
    return f"""<div class="sxbuy-in sxbuy-chooser">
<div class="sxbuy-top"><h3>{html.escape(button_label(summary))}</h3>{close}</div>
<p class="sxbuy-facts">{facts_text(summary, "<strong>" + title + "</strong>")} &middot; Buying accepts the <a href="{BASE_URL}/license">Licence</a> and <a href="{BASE_URL}/terms">Terms</a></p>
<div class="sxbuy-tabs" role="tablist">{tabs}</div>
{panels}
</div>"""


def render_html(summary):
    """Self-contained website embed: a button that opens the chooser in a dialog."""
    dialog_id = "sxbuy-" + summary["id"]
    return f"""<!-- SpawnXchange: Buy with your agent. Self-contained: inline CSS and JS, no external requests. -->
<style>{CSS}</style>
<div class="sxbuy"><button type="button" class="sxbuy-btn" data-sxbuy="open" data-for="{dialog_id}">{html.escape(button_label(summary))}</button><noscript> <a href="{BADGE_CAMPAIGN_URL}">Buy with your agent</a></noscript></div>
<dialog class="sxbuy" id="{dialog_id}" aria-label="Buy with your agent">
{chooser_body(summary, True)}
</dialog>
<script>{SCRIPT}</script>
"""


def render_page(summary):
    """A standalone page showing the chooser open, for a badge to link to."""
    title = html.escape(summary["title"]) or "This listing"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Buy {title} with your agent</title>
<style>{CSS}
body{{margin:0;background:#f6f8fa;font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}}
@media(prefers-color-scheme:dark){{body{{background:#010409}}}}
.sxbuy-page{{max-width:640px;margin:24px auto;border:1px solid var(--bd);border-radius:12px;background:var(--bg)}}
</style></head><body>
<main class="sxbuy sxbuy-page">
{chooser_body(summary, False)}
</main>
<script>{SCRIPT}</script>
</body></html>
"""


def build_snippet(item_id, fmt, chooser_url=None):
    """Fetch the item and return the block text. Raises SnippetError."""
    item_id = parse_item_id(item_id)
    if chooser_url is not None:
        if fmt != "md":
            raise SnippetError("--chooser-url only applies to --format md.")
        chooser_url = parse_chooser_url(chooser_url)
    summary = summarize(item_id, fetch_item(item_id))
    if fmt == "html":
        return render_html(summary)
    if fmt == "page":
        return render_page(summary)
    return render_markdown(summary, chooser_url)


def main():
    parser = argparse.ArgumentParser(
        description="Print a 'Buy with your agent' block for a live SpawnXchange listing. "
        "Read-only: one public GET, nothing is paid, signed or written."
    )
    parser.add_argument("--item", required=True, help="item id (UUID) of your active listing")
    parser.add_argument("--format", choices=["md", "html", "page"], default="md",
                        help="md: README block (default); html: self-contained embed for a "
                        "website, a button that opens a chooser; page: a standalone chooser page")
    parser.add_argument("--chooser-url",
                        help="md only: the page the badge links to (a hosted chooser page). "
                        "Default: the SpawnXchange campaign link")
    args = parser.parse_args()
    try:
        sys.stdout.write(build_snippet(args.item, args.format, args.chooser_url))
    except SnippetError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
