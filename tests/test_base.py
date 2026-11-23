"""Unit tests for the shared HTTP base (URL and timeout handling)."""

import pytest
import requests

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
