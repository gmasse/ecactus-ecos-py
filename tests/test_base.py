"""Unit tests for the shared HTTP base (URL and timeout handling)."""

import io
import time

import pytest
import requests
import urllib3

import ecactus
from ecactus.exceptions import HttpError, InitializationError


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid",
        "http://127.0.0.1:8080",
        "http://localhost:8080/",
        "http://[::1]:8080",
    ],
)
def test_accepted_url(url):
    """An https URL is accepted, and an http one on a loopback host only."""
    client = ecactus.AsyncEcos(url=url)
    assert client.url == url.rstrip("/")


@pytest.mark.parametrize(
    "url",
    ["http://example.invalid", "http://10.0.0.1", "ftp://example.invalid", "example"],
)
def test_rejected_url(url):
    """Any other URL would send the credentials in clear, or nowhere."""
    with pytest.raises(InitializationError):
        ecactus.AsyncEcos(url=url)


def test_http_error_message_is_truncated():
    """A long body is cut in the exception message and kept on the attribute."""
    body = "x" * 10_000
    exc = HttpError(502, body)
    assert len(str(exc)) < 400
    assert exc.message == body


def test_default_timeout():
    """A default per-request timeout is configured."""
    client = ecactus.AsyncEcos(url="https://example.invalid")
    assert client.timeout == 30.0


def test_custom_timeout_is_stored():
    """A caller-provided timeout overrides the default."""
    client = ecactus.AsyncEcos(url="https://example.invalid", timeout=5)
    assert client.timeout == 5


def test_timeout_can_be_disabled():
    """timeout=None disables the timeout (previous behaviour)."""
    client = ecactus.AsyncEcos(url="https://example.invalid", timeout=None)
    assert client.timeout is None


async def test_async_request_times_out(mock_server):
    """An aiohttp call exceeding the timeout raises instead of hanging."""
    client = ecactus.AsyncEcos(url=mock_server.url, timeout=0.1)
    with pytest.raises(TimeoutError):
        await client._async_get("/slow")  # noqa: SLF001


def test_sync_request_times_out(mock_server):
    """A requests call exceeding the timeout raises instead of hanging."""
    client = ecactus.Ecos(url=mock_server.url, timeout=0.1)
    with pytest.raises(requests.exceptions.Timeout):
        client._get("/slow")  # noqa: SLF001


def test_sync_total_timeout_covers_the_body(mock_server):
    """A body sent slowly enough that each read fits the timeout still times out."""
    client = ecactus.Ecos(url=mock_server.url, timeout=0.3)
    start = time.monotonic()
    with pytest.raises(requests.exceptions.Timeout):
        client._get("/drip", {"seconds": 2.0})  # noqa: SLF001
    assert time.monotonic() - start < 1.0


@pytest.mark.parametrize("timeout", [1.0, None])
def test_sync_slow_body_within_timeout(mock_server, timeout):
    """A body sent slowly but within the timeout, or with none, is read in full."""
    client = ecactus.Ecos(url=mock_server.url, timeout=timeout)
    assert client._get("/drip", {"seconds": 0.2}) == {"dripped": True}  # noqa: SLF001


def test_sync_timeout_without_a_socket(monkeypatch):
    """A response with no socket behind it, as under mock libraries, is read in full."""
    response = requests.Response()
    response.status_code = 200
    response.raw = urllib3.HTTPResponse(
        io.BytesIO(b'{"success": true, "data": {"mocked": true}}'),
        preload_content=False,
    )
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)
    client = ecactus.Ecos(url="https://example.invalid", timeout=1.0)
    assert client._get("/mocked") == {"mocked": True}  # noqa: SLF001
