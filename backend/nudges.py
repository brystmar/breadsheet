"""
Webhook nudges to Home Assistant (breadsheet#93; spec: API v2, Webhook nudges).

Each paired HA can register a webhook. Right after a change to a Fancy bake is saved, breadsheet POSTs `{}` to it:
"poll now". The nudge carries nothing, so a leaked URL can at most make HA poll early; HA then pulls the bakes
with its device token as usual. Best effort: sent from a background thread so the change's response never waits,
with a short timeout and no retries (HA's regular poll covers misses). A 404 or 410 means the webhook is gone,
so it's cleared.

Breadsheet calls a URL someone else chose, so it's careful (SSRF): https on port 443 only, no credentials in
the URL, no redirects, and only hosts that resolve to public addresses, checked both when the URL is registered
and again before each send. The send connects to the address that was just checked, not to whatever the name
resolves to a moment later, so a host can't pass the check and then point somewhere private (DNS rebinding).
Webhook URLs are secrets: never logged.
"""
import ipaddress
import logging
import socket
import ssl
from backend.database import db
from backend.devices import request_connection
from backend.models import Connection
from flask import current_app
from http.client import HTTPException, HTTPSConnection
from sqlalchemy import select
from threading import Thread
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

MAX_URL_LENGTH = 2000
TIMEOUT_SECONDS = 2
GONE = {404, 410}


def resolve(host: str) -> list[str]:
    """Every address a host name resolves to (replaced in tests)."""
    return [info[4][0] for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)]


def vet(url) -> tuple[str | None, list[str]]:
    """(why breadsheet won't call this URL, or None if it will; the public addresses its host resolves to)."""
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LENGTH:
        return f"Send an https URL of up to {MAX_URL_LENGTH} characters.", []
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return "That isn't a valid URL.", []
    if parts.scheme != 'https' or not parts.hostname:
        return "Webhooks must be https URLs.", []
    if parts.username or parts.password:
        return "Webhook URLs can't contain a username or password.", []
    if port not in (None, 443):
        return "Webhooks must use port 443.", []
    try:
        addresses = resolve(parts.hostname)
    except (OSError, UnicodeError):
        return "That host name doesn't resolve.", []
    if not addresses or not all(ipaddress.ip_address(address.split('%')[0]).is_global for address in addresses):
        return "Webhooks must be on the public internet.", []
    return None, addresses


def url_problem(url) -> str | None:
    """Why breadsheet won't call this URL, or None if it will."""
    return vet(url)[0]


class PinnedConnection(HTTPSConnection):
    """HTTPS to one already-checked address, with the certificate still verified against the host name."""

    def __init__(self, host: str, address: str):
        super().__init__(host, 443, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context())
        self._address = address

    def connect(self):
        sock = socket.create_connection((self._address, 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def send(url: str, address: str) -> int | None:
    """
    POST an empty nudge to `address`; the HTTP status, or None if it couldn't be sent (replaced in tests).
    Redirects aren't followed: a 3xx is just a status.
    """
    parts = urlsplit(url)
    connection = PinnedConnection(parts.hostname, address)
    try:
        connection.request('POST', (parts.path or '/') + (f'?{parts.query}' if parts.query else ''), body=b'{}',
                           headers={'Content-Type': 'application/json', 'User-Agent': 'breadsheet'})
        return connection.getresponse().status
    except (HTTPException, OSError, ValueError):
        return None
    finally:
        connection.close()


def run_in_background(work) -> None:
    """Run `work` without making the request wait (replaced in tests, which run it inline)."""
    Thread(target=work, daemon=True, name='nudges').start()


def deliver(app, targets: list[tuple]) -> None:
    """Send each nudge; clear webhooks that are gone. Runs outside the request, so it never raises."""
    with app.app_context():
        for connection_id, url in targets:
            try:
                problem, addresses = vet(url)
                if problem is not None:
                    logger.info("Skipped nudging connection %s: its webhook no longer resolves publicly", connection_id)
                    continue
                status = send(url, addresses[0])
                if status in GONE:
                    connection = db.session.get(Connection, connection_id)
                    if connection is not None and connection.webhook_url == url:
                        connection.webhook_url = None
                        db.session.commit()
                    logger.info("Cleared connection %s's webhook: it answered %s", connection_id, status)
                elif status is None or status >= 400:
                    logger.info("Nudge to connection %s failed (%s)", connection_id, status)
            except Exception:
                db.session.rollback()
                logger.exception("Nudging connection %s failed", connection_id)
        db.session.remove()


def nudge_home_assistants(user_id) -> None:
    """
    Nudge every Home Assistant the user has paired with a webhook, except the one making this request (it
    already knows). Call only after the change is committed. Costs the request one query; the sending happens
    in the background.
    """
    try:
        caller = request_connection()
        targets = [(connection.id, connection.webhook_url) for connection in db.session.scalars(select(Connection).where(
            Connection.user_id == user_id, Connection.revoked_at.is_(None), Connection.webhook_url.is_not(None)))
            if caller is None or connection.id != caller.id]
        if targets:
            app = current_app._get_current_object()
            run_in_background(lambda: deliver(app, targets))
    except Exception:
        # Never let a nudge break the change that triggered it
        db.session.rollback()
        logger.exception("Nudging Home Assistant failed for user %s", user_id)
