"""Reusable network resources with bounded retries and redacted observability."""

import logging
import socket
from typing import Final

import httpx2

LOGGER: Final = logging.getLogger(__name__)


async def log_response(response: httpx2.Response) -> None:
    """Log status only: never model bodies, URLs, headers or patient input."""
    LOGGER.info("provider_response status=%s", response.status_code)


def create_client() -> httpx2.AsyncClient:
    """Use tuned pooling; redirect suppression prevents credential forwarding."""
    limits = httpx2.Limits(max_connections=200, max_keepalive_connections=40, keepalive_expiry=30)
    transport = httpx2.AsyncHTTPTransport(
        http2=True,
        retries=3,
        limits=limits,
        socket_options=[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)],
    )
    return httpx2.AsyncClient(
        transport=transport,
        timeout=httpx2.Timeout(connect=5, read=30, write=10, pool=10),
        follow_redirects=False,
        event_hooks={"response": [log_response]},
    )
