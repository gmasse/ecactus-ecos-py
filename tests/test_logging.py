"""Unit tests for the redaction of tokens and personal data in logs."""

import logging

import pytest

import ecactus
from ecactus.base import _redact

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


async def test_async_debug_log_redacts_personal_identifiers(mock_server, caplog):
    """Names and serial numbers are masked; home and device IDs stay in clear."""
    caplog.set_level(logging.DEBUG, logger="ecactus")
    client = ecactus.AsyncEcos(email=LOGIN, password=PASSWORD, url=mock_server.url)
    await client.get_user()
    await client.get_homes()
    await client.get_all_devices()
    log = _library_log(caplog)
    for key in ("nickname", "homeName", "deviceAliasName", "deviceSn", "wifiSn"):
        assert f"'{key}': '<REDACTED>'" in log
    for value in ("My Home", "My Device", "SHC000000000000001", "azerty123456789"):
        assert value not in log
    assert "'homeId': '9876543210987654321'" in log
    assert "'deviceId': '1234567890123456789'" in log
    assert "'datacenterHost': 'https://api-ecos-eu.weiheng-tech.com'" in log


def test_sync_debug_log_redacts_personal_identifiers(mock_server, caplog):
    """Same guarantee for the synchronous client, firmware versions kept."""
    caplog.set_level(logging.DEBUG, logger="ecactus")
    client = ecactus.Ecos(email=LOGIN, password=PASSWORD, url=mock_server.url)
    client.get_devices("9876543210987654321")
    log = _library_log(caplog)
    assert "'deviceSn': '<REDACTED>'" in log
    assert "SHC000000000000001" not in log
    assert "'deviceId': '1234567890123456789'" in log
    assert "'emsSoftwareVersion': '000-00000-00'" in log


@pytest.mark.parametrize(
    "key",
    ["accessToken", "token", "access_token", "REFRESH_TOKEN", "Authorization"],
)
def test_redact_token_keys_keep_last_4_characters(key):
    """A key that looks like a token, in any case or spelling, is shortened."""
    assert _redact({key: "abcdefghijklmnop"}) == {key: "…mnop"}


@pytest.mark.parametrize("value", ["short", 12345, None, {"nested": "abcdefghijk"}])
def test_redact_token_keys_mask_other_values(value):
    """A token value too short to shorten, or not a string, is masked whole."""
    assert _redact({"token": value}) == {"token": "<REDACTED>"}


@pytest.mark.parametrize(
    "key",
    ["password", "newPassword", "clientSecret", "passwordToken", "Email", "PHONE"],
)
def test_redact_secret_and_personal_keys_mask_whole_value(key):
    """Secrets and personal data keep no character, whatever their case."""
    assert _redact({key: "abcdefghijklmnop"}) == {key: "<REDACTED>"}


def test_redact_walks_nested_bodies_and_keeps_other_keys():
    """Nested objects and lists are masked; other keys and values are kept."""
    body = {
        "code": 0,
        "data": [{"deviceSn": "SHC1", "deviceId": "42", "agentId": "7", "lat": 1.5}],
    }
    assert _redact(body) == {
        "code": 0,
        "data": [
            {
                "deviceSn": "<REDACTED>",
                "deviceId": "42",
                "agentId": "7",
                "lat": "<REDACTED>",
            }
        ],
    }
