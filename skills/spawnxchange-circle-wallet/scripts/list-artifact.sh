#!/usr/bin/env bash
#
# List a large artifact on SpawnXchange with a Circle Agent Wallet.
#
#   ./list-artifact.sh --archive FILE --title T --description-file F \
#       --tech-stack S --price-usdc N --wallet 0x... --chain BASE [--execute]
#
# Why this exists: `circle services pay` sends the request for you, which is what
# you want everywhere else — but it takes the request body as a single
# command-line argument, and the operating system caps one argument at 131,072
# bytes. Base64 inflates an archive by a third, so listing anything over roughly
# a 96 KB archive is impossible that way.
#
# An x402 payment authorizes the *charge*, not the contents of the request, so
# the two can be separated. This script uploads the archive itself as multipart —
# the bytes as they are, no base64 inflation, up to the API's 10 MB limit — and
# invokes `circle wallet sign typed-data` for the signature. The signing happens
# inside the Circle CLI, which already holds your key; this script only passes it
# the data to sign and takes back the signature.
#
# For an archive under ~96 KB you do not need this: use `circle services pay`.
#
# Preflight by default: it uploads the unpaid request, prints the fee the
# marketplace asks for, and stops. Pass --execute to pay it and publish.
#
# Requires: circle CLI (logged in), curl, jq.

list_artifact() {
  (
    set -euo pipefail

    local archive="" title="" description="" description_file="" tech_stack=""
    local price="" wallet="" chain="" base_url="https://spawnxchange.com" execute=0

    while [ $# -gt 0 ]; do
      case "$1" in
        --archive)          archive="$2"; shift 2 ;;
        --title)            title="$2"; shift 2 ;;
        --description)      description="$2"; shift 2 ;;
        --description-file) description_file="$2"; shift 2 ;;
        --tech-stack)       tech_stack="$2"; shift 2 ;;
        --price-usdc)       price="$2"; shift 2 ;;
        --wallet)           wallet="$2"; shift 2 ;;
        --chain)            chain="$2"; shift 2 ;;
        --base-url)         base_url="$2"; shift 2 ;;
        --execute)          execute=1; shift ;;
        *) echo "unknown argument: $1" >&2; return 2 ;;
      esac
    done

    # Circle's chain names are not the marketplace's, and the payment request uses
    # CAIP-2 ids. Map them here so a payment cannot be signed for a chain you did
    # not name.
    local network
    case "$chain" in
      BASE)          network="eip155:8453" ;;
      MATIC)         network="eip155:137" ;;
      BASE-SEPOLIA)  network="eip155:84532" ;;
      MATIC-AMOY)    network="eip155:80002" ;;
      *) echo "--chain must be BASE, MATIC, BASE-SEPOLIA or MATIC-AMOY" >&2; return 2 ;;
    esac

    [ -n "$archive" ] && [ -n "$title" ] && [ -n "$tech_stack" ] \
      && [ -n "$price" ] && [ -n "$wallet" ] \
      || { echo "missing a required argument; see the header of this script" >&2; return 2; }
    [ -f "$archive" ] || { echo "archive not found: $archive" >&2; return 2; }

    if [ -n "$description_file" ]; then
      description=$(cat "$description_file")
    fi
    [ -n "$description" ] || { echo "--description or --description-file is required" >&2; return 2; }

    # Refuse locally what the marketplace would refuse anyway, before sending bytes.
    local size
    size=$(wc -c < "$archive")
    if [ "$size" -gt $((10 * 1024 * 1024)) ]; then
      echo "archive is $size bytes; the limit is 10485760" >&2
      return 2
    fi
    if ! awk -v p="$price" 'BEGIN { exit !(p >= 0.1 && p <= 100) }'; then
      echo "price $price is outside the allowed band 0.1..100 USD" >&2
      return 2
    fi

    local work
    work=$(mktemp -d)
    chmod 700 "$work"
    trap 'rm -rf "$work"' EXIT

    jq -n --arg t "$title" --arg d "$description" --arg s "$tech_stack" \
          --argjson p "$price" \
      '{title: $t, description: $d, tech_stack: $s, prices: {USDC: $p}}' \
      > "$work/metadata.json"

    echo "archive   $archive ($size bytes)" >&2
    echo "listing   $title at $price USDC" >&2
    echo "wallet    $wallet on $chain" >&2
    echo >&2

    # The unpaid upload. Validation runs here, so a malformed listing is refused
    # now, for free. curl streams the file, so nothing passes through argv.
    local code
    code=$(curl -sS -o "$work/challenge.json" -w '%{http_code}' -X POST \
             -F "file=@${archive}" -F "metadata=<${work}/metadata.json" \
             "${base_url}/api/v1/items")
    if [ "$code" != "402" ]; then
      echo "expected a payment request, got HTTP $code:" >&2
      head -c 400 "$work/challenge.json" >&2; echo >&2
      return 1
    fi

    local requirement
    requirement=$(jq -c --arg net "$network" \
      'first(.accepts[] | select(.network == $net)) // empty' "$work/challenge.json")
    if [ -z "$requirement" ]; then
      echo "the marketplace offered no requirement for $network; it offered:" >&2
      jq -c '[.accepts[].network]' "$work/challenge.json" >&2
      return 1
    fi

    echo "fee       $(jq -r '.amount // .maxAmountRequired' <<<"$requirement") raw units of $(jq -r '.asset' <<<"$requirement")" >&2
    echo "          on $(jq -r '.network' <<<"$requirement") to $(jq -r '.payTo' <<<"$requirement")" >&2

    if [ "$execute" -ne 1 ]; then
      echo >&2
      echo "Nothing has been paid and nothing is listed. Re-run with --execute" >&2
      echo "to pay this fee and publish the artifact." >&2
      return 0
    fi

    # EIP-3009, exactly as the settlement path verifies it. The nonce is single-use.
    local nonce deadline
    nonce="0x$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    deadline=$(( $(date +%s) + $(jq -r '.maxTimeoutSeconds // 120' <<<"$requirement") ))

    jq -n --argjson r "$requirement" --arg from "$wallet" \
          --arg nonce "$nonce" --arg before "$deadline" '
      {
        types: { TransferWithAuthorization: [
          {name: "from", type: "address"}, {name: "to", type: "address"},
          {name: "value", type: "uint256"}, {name: "validAfter", type: "uint256"},
          {name: "validBefore", type: "uint256"}, {name: "nonce", type: "bytes32"}
        ]},
        primaryType: "TransferWithAuthorization",
        domain: {
          name: $r.extra.name, version: $r.extra.version,
          chainId: ($r.network | split(":")[1] | tonumber),
          verifyingContract: $r.asset
        },
        message: {
          from: $from, to: $r.payTo,
          value: (($r.amount // $r.maxAmountRequired) | tostring),
          validAfter: "0", validBefore: $before, nonce: $nonce
        }
      }' > "$work/typed.json"

    echo >&2
    echo "signing with the Circle CLI..." >&2
    local signature
    signature=$(npx --yes @circle-fin/cli wallet sign typed-data \
                  "$(jq -c . "$work/typed.json")" \
                  --address "$wallet" --chain "$chain" -q | tail -1 | tr -d ' \r')
    case "$signature" in
      0x*) ;;
      *) echo "expected a 0x signature from the Circle CLI, got: $signature" >&2; return 1 ;;
    esac

    local header
    header=$(jq -c -n --argjson r "$requirement" --argjson t "$(cat "$work/typed.json")" \
               --arg sig "$signature" --argjson c "$(cat "$work/challenge.json")" '
               {x402Version: 2, accepted: $r,
                payload: {signature: $sig, authorization: $t.message}}
               + (if $c.resource then {resource: $c.resource} else {} end)
               + (if $c.extensions then {extensions: $c.extensions} else {} end)' \
             | base64 -w 0)

    echo "paying and uploading..." >&2
    code=$(curl -sS -o "$work/result.json" -w '%{http_code}' -X POST \
             -H "PAYMENT-SIGNATURE: $header" \
             -F "file=@${archive}" -F "metadata=<${work}/metadata.json" \
             "${base_url}/api/v1/items")

    if [ "$code" = "202" ]; then
      jq . "$work/result.json"
      echo >&2
      echo "Listed. Poll the seller status request until it reaches active or" >&2
      echo "rejected, and save the invoice from invoice_url." >&2
      return 0
    fi

    if [ "$code" = "409" ] && jq -e '.error == "payment_settlement_pending"' "$work/result.json" >/dev/null; then
      echo >&2
      echo "The payment reached the chain but its outcome is not yet known." >&2
      jq -r '"  transaction \(.transaction)\n  network     \(.network)"' "$work/result.json" >&2
      echo "Do NOT run this again — a second attempt is a separate payment." >&2
      return 1
    fi

    echo "HTTP $code:" >&2
    head -c 400 "$work/result.json" >&2; echo >&2
    return 1
  )
}

list_artifact "$@"
