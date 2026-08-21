#!/usr/bin/env bash
set -euo pipefail

TUNNEL_NAME="${CLOUDFLARE_TUNNEL_NAME:-lunchbot-local}"
TUNNEL_HOSTNAME="${CLOUDFLARE_TUNNEL_HOSTNAME:-lunch-local.torbacka.se}"
TUNNEL_URL="${CLOUDFLARE_TUNNEL_URL:-http://127.0.0.1:5000}"
ORIGIN_CERT="${TUNNEL_ORIGIN_CERT:-$HOME/.cloudflared/cert.pem}"

usage() {
  cat <<EOF
Usage: $0 <setup|run|info|list>

Environment overrides:
  CLOUDFLARE_TUNNEL_NAME      default: lunchbot-local
  CLOUDFLARE_TUNNEL_HOSTNAME  default: lunch-local.torbacka.se
  CLOUDFLARE_TUNNEL_URL       default: http://127.0.0.1:5000

Examples:
  $0 setup
  $0 run
  CLOUDFLARE_TUNNEL_URL=http://127.0.0.1:5001 $0 run
EOF
}

require_cloudflared() {
  if ! command -v cloudflared >/dev/null 2>&1; then
    echo "cloudflared is not installed. Install it first: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    exit 1
  fi
}

ensure_login() {
  if [[ ! -f "$ORIGIN_CERT" ]]; then
    echo "No Cloudflare origin certificate found at $ORIGIN_CERT."
    echo "Opening Cloudflare login; pick the account/zone that owns $TUNNEL_HOSTNAME."
    cloudflared tunnel login
  fi
}

tunnel_exists() {
  cloudflared tunnel info "$TUNNEL_NAME" >/dev/null 2>&1
}

setup_tunnel() {
  ensure_login

  if tunnel_exists; then
    echo "Tunnel already exists: $TUNNEL_NAME"
  else
    cloudflared tunnel create "$TUNNEL_NAME"
  fi

  cloudflared tunnel route dns "$TUNNEL_NAME" "$TUNNEL_HOSTNAME"

  echo
  echo "Cloudflare tunnel is ready."
  echo "  name:     $TUNNEL_NAME"
  echo "  hostname: https://$TUNNEL_HOSTNAME"
  echo "  origin:   $TUNNEL_URL"
  echo
  echo "Run it with: $0 run"
}

run_tunnel() {
  ensure_login
  echo "Starting $TUNNEL_NAME at https://$TUNNEL_HOSTNAME -> $TUNNEL_URL"
  exec cloudflared tunnel run --url "$TUNNEL_URL" "$TUNNEL_NAME"
}

main() {
  require_cloudflared

  case "${1:-}" in
    setup)
      setup_tunnel
      ;;
    run)
      run_tunnel
      ;;
    info)
      cloudflared tunnel info "$TUNNEL_NAME"
      ;;
    list)
      cloudflared tunnel list
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
