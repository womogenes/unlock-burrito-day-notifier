# unlock-burrito-day-notifier

Tiny monitor for `https://unlockburritoday.com`.

It runs every 1 minute, follows redirects, and emails:

- `williamfeng1729@gmail.com`
- `calvinrodrigue@gmail.com`

if the final destination is not `chipotle.com` or a `chipotle.com` subdomain.

## Behavior

- Uses `requests` to `GET https://unlockburritoday.com`
- Treats the check as healthy only if the final hostname is `chipotle.com` or something like `www.chipotle.com`
- Sends one email to both recipients only when the request resolves and the final destination is wrong
- Skips email alerts for request failures such as DNS issues, connection errors, or timeouts
- Does not retry within a run
- Does not send recovery emails

Exit codes:

- `0`: healthy
- `1`: unhealthy, alert email sent
- `2`: configuration error or alert email failure

## Gmail prerequisite

Create a Google app password for the Gmail account you want to send from, then store the Gmail address and app password in `.env`.

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
GOOGLE_EMAIL=your-gmail-address@gmail.com
GOOGLE_APP_PASSWORD=replace-me
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
* * * * * cd /home/willi/unlock-burrito-day-notifier && /usr/bin/uv run python main.py >> /home/willi/unlock-burrito-day-notifier/logs/monitor.log 2>&1
```
