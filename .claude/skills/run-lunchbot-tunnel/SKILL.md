---
name: run-lunchbot-tunnel
description: Run or set up LunchBot's reusable local Cloudflare Tunnel for Slack development. Use when the user asks to start, run, inspect, create, route, or troubleshoot the static Cloudflare tunnel for this repo.
allowed-tools:
  - Bash
  - Read
---

# Run LunchBot Tunnel

Use this skill from the LunchBot repo root. It delegates tunnel operations to `scripts/cloudflare-tunnel.sh`, which owns the default tunnel configuration.

## Defaults

- Tunnel name: `lunchbot-local`
- Public hostname: `lunch-local.torbacka.se`
- Flask dev origin: `http://127.0.0.1:5000`
- Docker blue origin: `http://127.0.0.1:5001`
- Docker green origin: `http://127.0.0.1:5002`

## Workflow

1. Check that the helper exists and is executable:

```bash
test -x scripts/cloudflare-tunnel.sh
```

2. If the user asks for first-time setup, route the DNS hostname, or create the named tunnel:

```bash
scripts/cloudflare-tunnel.sh setup
```

If this opens Cloudflare login, tell the user to complete the browser login and select the Cloudflare account/zone that owns `lunch-local.torbacka.se`.

3. If the user asks to run/start the tunnel, choose the origin:

- Use Flask dev by default:

```bash
scripts/cloudflare-tunnel.sh run
```

- Use Docker blue when the user mentions Docker, Compose, blue, or port `5001`:

```bash
CLOUDFLARE_TUNNEL_URL=http://127.0.0.1:5001 scripts/cloudflare-tunnel.sh run
```

- Use Docker green when the user mentions green or port `5002`:

```bash
CLOUDFLARE_TUNNEL_URL=http://127.0.0.1:5002 scripts/cloudflare-tunnel.sh run
```

- Use a custom origin when the user provides a URL:

```bash
CLOUDFLARE_TUNNEL_URL=<url> scripts/cloudflare-tunnel.sh run
```

4. If the user asks for status or inspection:

```bash
scripts/cloudflare-tunnel.sh info
```

For account-level tunnel listing:

```bash
scripts/cloudflare-tunnel.sh list
```

## Slack URLs

When asked what to configure in Slack, use:

- OAuth redirect URL: `https://lunch-local.torbacka.se/slack/oauth_redirect`
- Slash command request URL: `https://lunch-local.torbacka.se/slack/command`
- Interactivity request URL: `https://lunch-local.torbacka.se/action`
- Events request URL: `https://lunch-local.torbacka.se/slack/events`

## Notes

- The tunnel run command is long-running. If started successfully, keep the session running and report the public URL to the user.
- Do not commit Cloudflare credentials or generated tunnel JSON files.
- If `cloudflared` is missing, tell the user to install it before using the skill.
