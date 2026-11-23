"""Tests that neither client follows an HTTP redirect.

Following one would send the request again wherever the `Location` header points,
another host or plain http, and the login request carries the email and password.
"""

import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import tracemalloc

import pytest

import ecactus
from ecactus.exceptions import HttpError, InvalidJsonError

from .conftest import LOGIN, PASSWORD  # noqa: TID251

ACCESS_TOKEN = "access-token-0123456789"
SUCCESS = {"code": 0, "message": "success", "success": True}
# What a redirect can carry: no body, a non-JSON body, or a JSON object that
# reads as a successful API response.
REDIRECT_BODIES = {
    "empty": b"",
    "text": b"Moved",
    "json": json.dumps({**SUCCESS, "data": {}}).encode(),
}
LARGE_BODY = b"x" * (8 * 1024 * 1024)


class _Server(ThreadingHTTPServer):
    """A loopback server that records the requests it receives."""

    def __init__(self, redirect_to: str | None) -> None:
        """Listen on a free port; redirect every request if `redirect_to` is set."""
        super().__init__(("127.0.0.1", 0), _Handler)
        self.redirect_to = redirect_to
        self.requests: list[str] = []
        self.url = f"http://127.0.0.1:{self.server_address[1]}"


class _Handler(BaseHTTPRequestHandler):
    # HTTP/1.0: one request per connection, so that a client which hangs up on
    # an unread body leaves no keep-alive connection to fail on.
    protocol_version = "HTTP/1.0"
    server: _Server

    def log_message(self, *args: object) -> None:
        """Keep the test output quiet."""

    def do_GET(self) -> None:
        """Answer a GET."""
        self._answer()

    def do_POST(self) -> None:
        """Answer a POST, once its body is read."""
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self._answer()

    def _answer(self) -> None:
        self.server.requests.append(f"{self.command} {self.path}")
        if self.server.redirect_to is None:
            # Plays a working API, so that a followed redirect would succeed.
            data = {"accessToken": "t" * 40, "refreshToken": "r" * 40}
            self._send(200, json.dumps({**SUCCESS, "data": data}).encode())
            return
        location: str | None = self.server.redirect_to + self.path
        status, body = 307, b""
        # /redirect/<status>/<body> and /no-location/<status>/<body>
        route = self.path.split("/")
        if route[1] in {"redirect", "no-location"}:
            status = int(route[2])
            body = LARGE_BODY if route[3] == "large" else REDIRECT_BODIES[route[3]]
            if route[1] == "no-location":
                location = None
        self._send(status, body, location)

    def _send(self, status: int, body: bytes, location: str | None = None) -> None:
        self.send_response(status)
        if location is not None:
            self.send_header("Location", location)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        # The client may stop reading a body larger than its limit.
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(body)


@pytest.fixture(scope="module")
def other_origin():
    """Start the origin the API redirects to."""
    server = _Server(redirect_to=None)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def redirecting_api(other_origin):
    """Start an API that answers every request with a redirect to the other origin."""
    server = _Server(redirect_to=other_origin.url)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def api_url(redirecting_api, other_origin):
    """Return the URL of the redirecting API, with no request recorded yet."""
    redirecting_api.requests.clear()
    other_origin.requests.clear()
    return redirecting_api.url


async def test_async_login_redirect_is_not_followed(api_url, other_origin):
    """A login answered with a 307 raises, and the password stays home."""
    client = ecactus.AsyncEcos(url=api_url, email=LOGIN, password=PASSWORD)
    with pytest.raises(HttpError) as exc_info:
        await client.login()
    assert exc_info.value.status_code == 307
    assert other_origin.requests == []
    assert client.access_token is None


def test_sync_login_redirect_is_not_followed(api_url, other_origin):
    """Same guarantee for the synchronous transport."""
    client = ecactus.Ecos(url=api_url, email=LOGIN, password=PASSWORD)
    with pytest.raises(HttpError) as exc_info:
        client.login()
    assert exc_info.value.status_code == 307
    assert other_origin.requests == []
    assert client.access_token is None


async def test_async_authenticated_get_redirect_is_not_followed(
    api_url, redirecting_api, other_origin
):
    """An authenticated GET answered with a 307 raises, and nothing reaches the other origin."""
    client = ecactus.AsyncEcos(url=api_url, access_token=ACCESS_TOKEN)
    with pytest.raises(HttpError) as exc_info:
        await client.get_user()
    assert exc_info.value.status_code == 307
    assert redirecting_api.requests == ["GET /api/client/settings/user/info"]
    assert other_origin.requests == []


def test_sync_authenticated_get_redirect_is_not_followed(
    api_url, redirecting_api, other_origin
):
    """Same guarantee for the synchronous transport."""
    client = ecactus.Ecos(url=api_url, access_token=ACCESS_TOKEN)
    with pytest.raises(HttpError) as exc_info:
        client.get_user()
    assert exc_info.value.status_code == 307
    assert redirecting_api.requests == ["GET /api/client/settings/user/info"]
    assert other_origin.requests == []


@pytest.mark.parametrize("kind", REDIRECT_BODIES)
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("route", ["redirect", "no-location"])
async def test_async_redirect_raises_http_error(
    api_url, other_origin, route, status, kind
):
    """Whatever its body, with a Location or not, a 3xx raises HttpError with its status."""
    client = ecactus.AsyncEcos(url=api_url)
    for call in (client._async_get, client._async_post):  # noqa: SLF001
        with pytest.raises(HttpError) as exc_info:
            await call(f"/{route}/{status}/{kind}")
        assert exc_info.value.status_code == status
    assert other_origin.requests == []


@pytest.mark.parametrize("kind", REDIRECT_BODIES)
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("route", ["redirect", "no-location"])
def test_sync_redirect_raises_http_error(api_url, other_origin, route, status, kind):
    """Same guarantee for the synchronous transport."""
    client = ecactus.Ecos(url=api_url)
    for call in (client._get, client._post):  # noqa: SLF001
        with pytest.raises(HttpError) as exc_info:
            call(f"/{route}/{status}/{kind}")
        assert exc_info.value.status_code == status
    assert other_origin.requests == []


async def test_async_redirect_body_size_is_limited(api_url, monkeypatch):
    """The body of a redirect is read under MAX_RESPONSE_BYTES too."""
    monkeypatch.setattr(ecactus.base, "MAX_RESPONSE_BYTES", 65536)
    client = ecactus.AsyncEcos(url=api_url)
    with pytest.raises(InvalidJsonError, match="larger than 65536 bytes"):
        await client._async_get("/redirect/307/large")  # noqa: SLF001


def test_sync_redirect_body_is_not_read(api_url):
    """The synchronous transport rejects a redirect before reading its body.

    `requests` reads the whole body of a redirect, even one it does not follow,
    outside of the MAX_RESPONSE_BYTES limit.
    """
    client = ecactus.Ecos(url=api_url)
    tracemalloc.start()
    try:
        with pytest.raises(HttpError) as exc_info:
            client._get("/redirect/307/large")  # noqa: SLF001
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert exc_info.value.status_code == 307
    assert peak < len(LARGE_BODY) // 2
