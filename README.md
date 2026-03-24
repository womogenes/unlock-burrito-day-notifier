# unlock-burrito-day-notifier

Tiny monitor for `https://unlockburritoday.com`.

It runs every 5 minutes, follows redirects, and emails:

- `williamfeng1729@gmail.com`
- `calvinrodrigue@gmail.com`

if the final destination is not `chipotle.com` or a `chipotle.com` subdomain.

## Behavior

- Uses `requests` to `GET https://unlockburritoday.com`
- Treats the check as healthy only if the final hostname is `chipotle.com` or something like `www.chipotle.com`
- Sends one email to both recipients on every failed cron run
- Does not retry within a run
- Does not send recovery emails

Exit codes:

- `0`: healthy
- `1`: unhealthy, alert email sent
- `2`: configuration error or alert email failure

## SMTP prerequisite

`wfeng.dev` already has Cloudflare Email Routing for inbound mail. That does not provide outbound SMTP.

Before using `ALERT_FROM=noreply@wrapd.wfeng.dev`, provision an SMTP-capable outbound mail service for that domain and collect:

- SMTP host
- SMTP port
- SMTP username
- SMTP password
- SMTP security mode: `starttls` or `ssl`

## Setup

1. Create a local `.env` file in the project root. Start from `.env.example`.
1. Install dependencies:

```bash
uv sync
```

1. Run one manual check:

```bash
uv run python main.py
```

## Environment variables

```dotenv
SMTP_HOST=smtp.your-provider.example
SMTP_PORT=587
SMTP_USERNAME=noreply@wrapd.wfeng.dev
SMTP_PASSWORD=replace-me
SMTP_SECURITY=starttls
ALERT_FROM=noreply@wrapd.wfeng.dev
```

## Remote deploy

On `ssh.womogenes.com`, clone this repo to:

```text
/home/willi/unlock-burrito-day-notifier
```

Then install dependencies and create `.env`.

## Cron

Create the log directory if needed:

```bash
mkdir -p /home/willi/unlock-burrito-day-notifier/logs
```

Install this cron entry:

```cron
*/5 * * * * cd /home/willi/unlock-burrito-day-notifier && /usr/bin/uv run python main.py >> /home/willi/unlock-burrito-day-notifier/logs/monitor.log 2>&1
```
