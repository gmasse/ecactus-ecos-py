"""Unit tests for the shared HTTP base (timeout handling)."""

import pytest
import requests

import ecactus


def test_default_timeout():
    """A default per-request timeout is configured."""
    client = ecactus.AsyncEcos(url="http://example.invalid")
    assert client.timeout == 30.0


def test_custom_timeout_is_stored():
    """A caller-provided timeout overrides the default."""
    client = ecactus.AsyncEcos(url="http://example.invalid", timeout=5)
    assert client.timeout == 5


def test_timeout_can_be_disabled():
    """timeout=None disables the timeout (previous behaviour)."""
    client = ecactus.AsyncEcos(url="http://example.invalid", timeout=None)
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
