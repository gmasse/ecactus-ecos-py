"""Unit tests for robust handling of malformed API responses."""

import pytest

import ecactus
from ecactus.exceptions import (
    ApiResponseError,
    EcosApiError,
    HttpError,
    InvalidJsonError,
)


async def test_async_malformed_response_raises_library_error(mock_server):
    """Valid JSON without the expected envelope keys must raise a library error.

    Previously the code indexed ``body["success"]`` / ``body["code"]`` directly,
    so a response missing those keys raised a bare ``KeyError`` that callers
    could not catch via the documented ``EcosApiError`` hierarchy.
    """
    client = ecactus.AsyncEcos(url=mock_server.url)
    with pytest.raises(EcosApiError) as exc_info:
        await client._async_get("/malformed")  # noqa: SLF001
    assert isinstance(exc_info.value, ApiResponseError)


def test_sync_malformed_response_raises_library_error(mock_server):
    """Same guarantee for the synchronous transport."""
    client = ecactus.Ecos(url=mock_server.url)
    with pytest.raises(EcosApiError):
        client._get("/malformed")  # noqa: SLF001


async def test_async_non_json_error_keeps_http_status(mock_server):
    """A non-JSON error page must raise HttpError with its status code."""
    client = ecactus.AsyncEcos(url=mock_server.url)
    with pytest.raises(HttpError) as exc_info:
        await client._async_get("/not-the-api")  # noqa: SLF001
    assert exc_info.value.status_code == 404


def test_sync_non_json_error_keeps_http_status(mock_server):
    """Same guarantee for the synchronous transport.

    A ``requests.Response`` is falsy for any 4xx/5xx, so testing ``if response``
    used to turn such a page into InvalidJsonError.
    """
    client = ecactus.Ecos(url=mock_server.url)
    with pytest.raises(HttpError) as exc_info:
        client._get("/not-the-api")  # noqa: SLF001
    assert exc_info.value.status_code == 404


@pytest.mark.parametrize("path", ["/non-object", "/invalid-json", "/deep-json"])
async def test_async_unusable_json_raises_invalid_json(mock_server, path):
    """A body that is not a JSON object raises InvalidJsonError.

    This covers JSON that is a list, a JSON content type over a body that does not
    parse, and nesting deep enough to exhaust the parser's recursion limit.
    """
    client = ecactus.AsyncEcos(url=mock_server.url)
    with pytest.raises(InvalidJsonError):
        await client._async_get(path)  # noqa: SLF001


@pytest.mark.parametrize("path", ["/non-object", "/invalid-json", "/deep-json"])
def test_sync_unusable_json_raises_invalid_json(mock_server, path):
    """Same guarantee for the synchronous transport."""
    client = ecactus.Ecos(url=mock_server.url)
    with pytest.raises(InvalidJsonError):
        client._get(path)  # noqa: SLF001


async def test_async_post_non_object_raises_invalid_json(mock_server):
    """The POST transport checks the shape of the body too."""
    client = ecactus.AsyncEcos(url=mock_server.url)
    with pytest.raises(InvalidJsonError):
        await client._async_post("/non-object")  # noqa: SLF001


def test_sync_post_non_object_raises_invalid_json(mock_server):
    """Same guarantee for the synchronous transport."""
    client = ecactus.Ecos(url=mock_server.url)
    with pytest.raises(InvalidJsonError):
        client._post("/non-object")  # noqa: SLF001


async def test_async_response_size_is_limited(mock_server, monkeypatch):
    """A body larger than MAX_RESPONSE_BYTES raises instead of being read whole."""
    monkeypatch.setattr(ecactus.base, "MAX_RESPONSE_BYTES", 8)
    client = ecactus.AsyncEcos(url=mock_server.url)
    with pytest.raises(InvalidJsonError, match="larger than 8 bytes"):
        await client._async_get("/malformed")  # noqa: SLF001


def test_sync_response_size_is_limited(mock_server, monkeypatch):
    """Same guarantee for the synchronous transport."""
    monkeypatch.setattr(ecactus.base, "MAX_RESPONSE_BYTES", 8)
    client = ecactus.Ecos(url=mock_server.url)
    with pytest.raises(InvalidJsonError, match="larger than 8 bytes"):
        client._get("/malformed")  # noqa: SLF001
