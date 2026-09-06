#!/usr/bin/env bash
#
# Run one SpawnXchange x402 call with a CDP-managed wallet.
#
#   WALLET_ADDRESS=0x... ./x402-call.sh [FLAGS] <METHOD> <URL> [BODY]
#   WALLET_ADDRESS=0x... ./x402-call.sh [FLAGS] <METHOD> <URL> --multipart <curl args...>
#
#     BODY         inline JSON, or @/path/to/file to stream a large body from disk
#     --multipart  everything after it is passed to curl verbatim, for
#                  `-F file=@artifact.zip -F metadata={...}` uploads. Use this for
#                  a large archive: multipart sends the bytes as they are, while
#                  base64-in-JSON adds a third to every one of them.
#
#   FLAGS, before the method:
#
#     --execute            required before anything that actually costs money
#     --network <caip2>    which chain to pay on, e.g. eip155:8453
#
# Works for paid routes and for free 0 USDC identity routes alike — the amount
# comes from the challenge, not from here. A free call runs as-is; a call that
# would spend money prints the price and stops unless --execute is given, so the
# cost is always seen before it is paid. Prints the final response body on stdout
# and the price on stderr.
#
# Requires: cdp CLI (`cdp env live`), curl, jq.

x402_call() {
  (
    set -euo pipefail

    local execute=0 network=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --execute) execute=1; shift ;;
        --network) network="$2"; shift 2 ;;
        *) break ;;
      esac
    done

    local method="${1:?method required, e.g. GET or POST}"
    local url="${2:?url required}"
    local wallet="${WALLET_ADDRESS:?WALLET_ADDRESS must be set to your CDP wallet address}"
    shift 2

    local work
    work=$(mktemp -d)
    chmod 700 "$work"
    trap 'rm -rf "$work"' EXIT

    # curl arguments for the request body, shared by the probe and the retry.
    # Both requests must carry the same body: the challenge is issued against a
    # validated request, and the retry has to be that same request plus a header.
    local -a body_args=()
    if [ "${1:-}" = "--multipart" ]; then
      shift
      # Passed through verbatim. No Content-Type here — curl sets it, with the
      # boundary, and overriding it breaks the upload.
      body_args=("$@")
    elif [ -n "${1:-}" ]; then
      case "$1" in
        @*) body_args=(-H "Content-Type: application/json" --data-binary "$1") ;;
        *)  body_args=(-H "Content-Type: application/json" --data "$1") ;;
      esac
    fi

    # 1. Unsigned probe. The reply is the 402 carrying the requirements to sign.
    curl -sS -X "$method" "${body_args[@]}" "$url" > "$work/challenge.json"

    if ! jq -e '.accepts' "$work/challenge.json" >/dev/null 2>&1; then
      # Not a challenge: either the route is public, or it refused us outright
      # (403 region_unavailable, 400 validation, ...). Either way, show it.
      cat "$work/challenge.json"
      return 0
    fi

    # Narrow to one chain when asked, so a payment cannot be signed for a network
    # you did not choose. Without --network the challenge is passed through as it
    # came, and CDP picks.
    if [ -n "$network" ]; then
      jq -c --arg net "$network" '[.accepts[] | select(.network == $net)]' \
        "$work/challenge.json" > "$work/accepts.json"
      if [ "$(cat "$work/accepts.json")" = "[]" ]; then
        echo "the challenge offers no requirement for $network; it offered:" >&2
        jq -c '[.accepts[].network]' "$work/challenge.json" >&2
        return 1
      fi
    else
      jq -c '.accepts' "$work/challenge.json" > "$work/accepts.json"
    fi

    jq -r '.[] | "  price: \(.amount) raw on \(.network) -> \(.payTo)"' \
      "$work/accepts.json" >&2

    # A zero-amount challenge is the identity handshake: it proves who you are and
    # moves no money, so it needs no confirmation. Anything else spends USDC.
    local amount
    amount=$(jq -r 'first(.[].amount // .[].maxAmountRequired) // "0"' "$work/accepts.json")
    if [ "$amount" != "0" ] && [ "$execute" -ne 1 ]; then
      echo >&2
      echo "This request costs $amount raw units. Nothing has been paid." >&2
      echo "Re-run with --execute as the first argument to pay it." >&2
      return 3
    fi

    if [ -z "$network" ] && [ "$amount" != "0" ] \
       && [ "$(jq 'length' "$work/accepts.json")" -gt 1 ]; then
      echo "the challenge offers several chains; pass --network to choose one" >&2
      jq -c '[.[].network]' "$work/accepts.json" >&2
      return 1
    fi

    # 2. Typed data from those exact requirements.
    cdp util x402 build --from "$wallet" \
      --payment-requirements "$(cat "$work/accepts.json")" \
      > "$work/typed_data.json"

    # 3. Sign. The key never leaves CDP.
    cdp evm accounts sign typed-data "$wallet" \
      primaryType="$(jq -r '.primaryType' "$work/typed_data.json")" \
      domain:="$(jq -c '.domain' "$work/typed_data.json")" \
      message:="$(jq -c '.message' "$work/typed_data.json")" \
      types:="$(jq -c '.types' "$work/typed_data.json")" \
      | jq -r '.signature' > "$work/signature.txt"

    # 4. Encode and retry. Requirements, signature and authorization must all come
    #    from this one challenge — nonces are single-use and windows are short.
    cdp util x402 encode --x402-version 2 \
      --payment-requirements "$(cat "$work/accepts.json")" \
      --signature "$(cat "$work/signature.txt")" \
      --authorization "$(jq -c '.message' "$work/typed_data.json")" > "$work/header.txt"

    curl -sS -X "$method" \
      -H "PAYMENT-SIGNATURE: $(cat "$work/header.txt")" \
      "${body_args[@]}" "$url"
  )
}

x402_call "$@"
