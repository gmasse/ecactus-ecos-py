"""Unit tests for the redaction of tokens and personal data in logs."""

import logging

import pytest

import ecactus

from .conftest import LOGIN, PASSWORD  # noqa: TID251


def _library_log(caplog: pytest.LogCaptureFixture) -> str:
    """Return the messages the library logged, leaving out the mock server's."""
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "ecactus" or record.name.startswith("ecactus.")
    )


async def test_async_debug_log_redacts_tokens(mock_server, caplog):
    """Root and `ecactus` at DEBUG log neither the tokens nor the email."""
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="ecactus")
    client = ecactus.AsyncEcos(email=LOGIN, password=PASSWORD, url=mock_server.url)
    await client.get_user()
    log = _library_log(caplog)
    assert "guide/login -> HTTP 200" in log
    assert mock_server.access_token not in log
    assert mock_server.refresh_token not in log
    assert "…" + mock_server.access_token[-4:] in log
    assert LOGIN not in log


def test_sync_debug_log_redacts_tokens(mock_server, caplog):
    """Same guarantee for the synchronous client."""
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="ecactus")
    client = ecactus.Ecos(email=LOGIN, password=PASSWORD, url=mock_server.url)
    client.get_user()
    log = _library_log(caplog)
    assert "guide/login -> HTTP 200" in log
    assert mock_server.access_token not in log
    assert mock_server.refresh_token not in log
    assert LOGIN not in log


async def test_wire_log_shows_raw_bodies(mock_server, caplog):
    """Naming `ecactus.wire` logs the raw bodies, tokens included."""
    caplog.set_level(logging.DEBUG, logger="ecactus.wire")
    client = ecactus.AsyncEcos(email=LOGIN, password=PASSWORD, url=mock_server.url)
    await client.login()
    assert mock_server.access_token in _library_log(caplog)
