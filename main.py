from __future__ import annotations

import os
import smtplib
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests

CHECK_URL = "https://unlockburritoday.com"
EXPECTED_HOST = "chipotle.com"
ALERT_RECIPIENTS = [
    "williamfeng1729@gmail.com",
    "calvinrodrigue@gmail.com",
]
REQUEST_TIMEOUT_SECONDS = 15
PROJECT_DIR = Path(__file__).resolve().parent
ENV_PATH = PROJECT_DIR / ".env"


@dataclass(frozen=True)
class GmailConfig:
    email: str
    app_password: str


@dataclass(frozen=True)
class CheckResult:
    is_healthy: bool
    did_resolve: bool
    status_code: int | None
    final_url: str | None
    details: str


def log(message: str, *, err: bool = False) -> None:
    stream = sys.stderr if err else sys.stdout
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    lines = message.splitlines() or [""]
    for line in lines:
        print(f"[{timestamp}] {line}", file=stream)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        key, separator, value = line.partition("=")
        if separator != "=":
            raise ValueError(f"Invalid .env line: {raw_line!r}")

        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def load_gmail_config() -> GmailConfig:
    if not (
        os.environ.get("GOOGLE_EMAIL")
        and os.environ.get("GOOGLE_APP_PASSWORD")
    ):
        load_env_file(ENV_PATH)

    missing_keys = [
        key
        for key in ("GOOGLE_EMAIL", "GOOGLE_APP_PASSWORD")
        if not os.environ.get(key)
    ]
    if missing_keys:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")

    return GmailConfig(
        email=os.environ["GOOGLE_EMAIL"].strip(),
        app_password=os.environ["GOOGLE_APP_PASSWORD"],
    )


def is_expected_host(hostname: str | None) -> bool:
    if not hostname:
        return False

    host = hostname.lower()
    return host == EXPECTED_HOST or host.endswith(f".{EXPECTED_HOST}")


def format_redirect_history(response: requests.Response) -> Iterable[str]:
    for redirect in response.history:
        yield (
            f"{redirect.status_code} {redirect.url} "
            f"-> {redirect.headers.get('Location', '<no location header>')}"
        )

    yield f"{response.status_code} {response.url}"


def check_redirect() -> CheckResult:
    response = requests.get(CHECK_URL, allow_redirects=True, timeout=REQUEST_TIMEOUT_SECONDS)
    final_hostname = urlparse(response.url).hostname
    history_text = "\n".join(format_redirect_history(response))

    if is_expected_host(final_hostname):
        return CheckResult(
            is_healthy=True,
            did_resolve=True,
            status_code=response.status_code,
            final_url=response.url,
            details=history_text,
        )

    details = (
        "Redirect did not end on chipotle.com.\n"
        f"Observed final hostname: {final_hostname or '<missing>'}\n"
        f"Redirect chain:\n{history_text}"
    )
    return CheckResult(
        is_healthy=False,
        did_resolve=True,
        status_code=response.status_code,
        final_url=response.url,
        details=details,
    )


def build_alert_message(result: CheckResult, alert_from: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = alert_from
    message["To"] = ", ".join(ALERT_RECIPIENTS)
    message["Subject"] = "unlockburritoday.com is not redirecting to chipotle.com"
    message.set_content(
        "\n".join(
            [
                "unlockburritoday.com failed its redirect check.",
                f"Timestamp (UTC): {datetime.now(UTC).isoformat()}",
                f"Monitored URL: {CHECK_URL}",
                f"Expected host: {EXPECTED_HOST}",
                f"Observed status code: {result.status_code if result.status_code is not None else '<none>'}",
                f"Observed final URL: {result.final_url or '<none>'}",
                "",
                result.details,
            ]
        )
    )
    return message


def send_alert_email(config: GmailConfig, message: EmailMessage) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(config.email, config.app_password)
        server.send_message(message)


def main() -> int:
    try:
        gmail_config = load_gmail_config()
    except Exception as exc:
        log(f"Configuration error: {exc}", err=True)
        return 2

    try:
        result = check_redirect()
    except Exception as exc:
        result = CheckResult(
            is_healthy=False,
            did_resolve=False,
            status_code=None,
            final_url=None,
            details=f"Request failed with exception: {exc!r}",
        )

    if result.is_healthy:
        log(
            f"healthy: {CHECK_URL} -> {result.final_url} "
            f"(status={result.status_code})"
        )
        return 0

    if not result.did_resolve:
        print(f"skipping alert: {result.details}")
        return 0

    message = build_alert_message(result, gmail_config.email)
    try:
        send_alert_email(gmail_config, message)
    except Exception as exc:
        log("Redirect check failed and alert email could not be sent.", err=True)
        log(result.details, err=True)
        log(f"Email error: {exc!r}", err=True)
        return 2

    log("Alert email sent.")
    log(result.details)
    return 1


if __name__ == "__main__":
    raise SystemExit() #(main())
