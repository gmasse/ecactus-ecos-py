"""Unit tests for robust handling of malformed API responses."""

import pytest

import ecactus
from ecactus.exceptions import ApiResponseError, EcosApiError


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
