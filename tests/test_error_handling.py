"""Unit tests for robust handling of malformed API responses."""

from datetime import datetime

from pydantic import ValidationError
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


@pytest.mark.parametrize("charset", ["undefined", "idna"])
async def test_async_undecodable_charset_falls_back_to_utf8(mock_server, charset):
    """A charset that cannot decode the body falls back to UTF-8.

    `undefined` always raises UnicodeError, and `idna` refuses `errors="replace"`.
    """
    client = ecactus.AsyncEcos(url=mock_server.url)
    assert await client._async_get(f"/charset/{charset}") == {}  # noqa: SLF001


@pytest.mark.parametrize("charset", ["undefined", "idna"])
def test_sync_undecodable_charset_falls_back_to_utf8(mock_server, charset):
    """Same guarantee for the synchronous transport."""
    client = ecactus.Ecos(url=mock_server.url)
    assert client._get(f"/charset/{charset}") == {}  # noqa: SLF001


# `data` of the wrong type, served by the mock server under /hostile/<scenario>/
WRONG_DATA = ["null", "missing", "string", "list"]

# Client methods whose `data` goes through a model, with the arguments they need
MODEL_METHODS = [
    ("get_user", ()),
    ("get_homes", ()),
    ("get_devices", ("home",)),
    ("get_all_devices", ()),
    ("get_today_device_data", ("device",)),
    ("get_realtime_home_data", ("home",)),
    ("get_realtime_device_data", ("device",)),
    ("get_history", ("device", 4)),
    ("get_insight", ("device", 5)),
]

# Series a model validator would have called `.keys()` or `.get()` on, and
# timestamp keys that are not numbers
MALFORMED_SERIES = [
    ("series-list", "get_today_device_data", ("device",)),
    ("series-string", "get_today_device_data", ("device",)),
    ("timestamp-not-a-number", "get_today_device_data", ("device",)),
    ("other-series-bool", "get_today_device_data", ("device",)),
    ("metrics-not-a-list", "get_today_device_data", ("device",)),
    ("series-list", "get_history", ("device", 4)),
    ("series-string", "get_history", ("device", 4)),
    ("timestamp-not-a-number", "get_history", ("device", 4)),
    ("insight-series-list", "get_insight", ("device", 5)),
    ("insight-consumption-list", "get_insight", ("device", 5)),
    ("insight-other-series-number", "get_insight", ("device", 5)),
    ("insight-metrics-not-a-list", "get_insight", ("device", 5)),
]

# Fault event pages whose events a model validator would have choked on
MALFORMED_EVENTS = ["events-null", "event-code-list", "event-type-number"]

EVENT_PERIOD = (datetime(2025, 3, 1), datetime(2025, 3, 2))


# List endpoints, whose `data` goes through an adapter rather than a model
LIST_METHODS = [
    ("list", "get_homes", ()),
    ("list", "get_devices", ("home",)),
    ("list", "get_all_devices", ()),
    ("event-type-number", "get_fault_events", ("device", *EVENT_PERIOD)),
]


def hostile_url(mock_server, scenario):
    """Return the URL of an API whose responses carry the scenario's `data`."""
    return f"{mock_server.url}/hostile/{scenario}"


@pytest.mark.parametrize("scenario", [*WRONG_DATA, "tokens-not-strings"])
async def test_async_login_without_tokens_raises_invalid_json(mock_server, scenario):
    """A successful login response without string tokens raises InvalidJsonError."""
    client = ecactus.AsyncEcos(
        url=hostile_url(mock_server, scenario), email="user", password="password"
    )
    with pytest.raises(InvalidJsonError, match="no access and refresh tokens"):
        await client.login()
    assert client.access_token is None
    assert client.refresh_token is None


@pytest.mark.parametrize("scenario", [*WRONG_DATA, "tokens-not-strings"])
def test_sync_login_without_tokens_raises_invalid_json(mock_server, scenario):
    """Same guarantee for the synchronous client."""
    client = ecactus.Ecos(
        url=hostile_url(mock_server, scenario), email="user", password="password"
    )
    with pytest.raises(InvalidJsonError, match="no access and refresh tokens"):
        client.login()
    assert client.access_token is None
    assert client.refresh_token is None


@pytest.mark.parametrize("scenario", WRONG_DATA)
@pytest.mark.parametrize(("method", "args"), MODEL_METHODS)
async def test_async_wrong_data_raises_validation_error(
    mock_server, method, args, scenario
):
    """`data` that is not what the model expects raises a ValidationError.

    Unpacking it with `Model(**data)` or iterating over it raised a TypeError.
    """
    client = ecactus.AsyncEcos(
        url=hostile_url(mock_server, scenario), access_token="token"
    )
    with pytest.raises(ValidationError):
        await getattr(client, method)(*args)


@pytest.mark.parametrize("scenario", WRONG_DATA)
@pytest.mark.parametrize(("method", "args"), MODEL_METHODS)
def test_sync_wrong_data_raises_validation_error(mock_server, method, args, scenario):
    """Same guarantee for the synchronous client."""
    client = ecactus.Ecos(url=hostile_url(mock_server, scenario), access_token="token")
    with pytest.raises(ValidationError):
        getattr(client, method)(*args)


@pytest.mark.parametrize(("scenario", "method", "args"), MALFORMED_SERIES)
async def test_async_malformed_series_raises_validation_error(
    mock_server, scenario, method, args
):
    """A malformed series raises a ValidationError, not an AttributeError."""
    client = ecactus.AsyncEcos(
        url=hostile_url(mock_server, scenario), access_token="token"
    )
    with pytest.raises(ValidationError):
        await getattr(client, method)(*args)


@pytest.mark.parametrize(("scenario", "method", "args"), MALFORMED_SERIES)
def test_sync_malformed_series_raises_validation_error(
    mock_server, scenario, method, args
):
    """Same guarantee for the synchronous client."""
    client = ecactus.Ecos(url=hostile_url(mock_server, scenario), access_token="token")
    with pytest.raises(ValidationError):
        getattr(client, method)(*args)


async def test_async_null_series_holds_no_data(mock_server):
    """A null series holds no data, like an absent one."""
    client = ecactus.AsyncEcos(
        url=hostile_url(mock_server, "series-null"), access_token="token"
    )
    assert (await client.get_today_device_data("device")).metrics == []
    assert (await client.get_history("device", 4)).metrics == []

    client.url = hostile_url(mock_server, "other-series-null")
    [power] = (await client.get_today_device_data("device")).metrics
    assert power.home == 1.0
    assert power.solar is None

    client.url = hostile_url(mock_server, "insight-other-series-null")
    insight = await client.get_insight("device", 5)
    assert insight.energy_timeseries is not None
    [energy] = insight.energy_timeseries.metrics
    assert energy.home == 1.0
    assert energy.eps is None


def test_sync_null_series_holds_no_data(mock_server):
    """Same guarantee for the synchronous client."""
    client = ecactus.Ecos(
        url=hostile_url(mock_server, "series-null"), access_token="token"
    )
    assert client.get_today_device_data("device").metrics == []
    assert client.get_history("device", 4).metrics == []

    client.url = hostile_url(mock_server, "other-series-null")
    [power] = client.get_today_device_data("device").metrics
    assert power.home == 1.0
    assert power.solar is None

    client.url = hostile_url(mock_server, "insight-other-series-null")
    insight = client.get_insight("device", 5)
    assert insight.energy_timeseries is not None
    [energy] = insight.energy_timeseries.metrics
    assert energy.home == 1.0
    assert energy.eps is None


@pytest.mark.parametrize("scenario", WRONG_DATA)
async def test_async_fault_events_not_an_object_raises_invalid_json(
    mock_server, scenario
):
    """A fault event page that is not an object raises InvalidJsonError."""
    client = ecactus.AsyncEcos(
        url=hostile_url(mock_server, scenario), access_token="token"
    )
    with pytest.raises(InvalidJsonError):
        await client.get_fault_events("device", *EVENT_PERIOD)


@pytest.mark.parametrize("scenario", WRONG_DATA)
def test_sync_fault_events_not_an_object_raises_invalid_json(mock_server, scenario):
    """Same guarantee for the synchronous client."""
    client = ecactus.Ecos(url=hostile_url(mock_server, scenario), access_token="token")
    with pytest.raises(InvalidJsonError):
        client.get_fault_events("device", *EVENT_PERIOD)


@pytest.mark.parametrize("scenario", MALFORMED_EVENTS)
async def test_async_malformed_events_raise_validation_error(mock_server, scenario):
    """Malformed events raise a ValidationError.

    A list as error code was looked up in the event catalog (TypeError), and a
    number as event type was lowercased (AttributeError).
    """
    client = ecactus.AsyncEcos(
        url=hostile_url(mock_server, scenario), access_token="token"
    )
    with pytest.raises(ValidationError):
        await client.get_fault_events("device", *EVENT_PERIOD)


@pytest.mark.parametrize("scenario", MALFORMED_EVENTS)
def test_sync_malformed_events_raise_validation_error(mock_server, scenario):
    """Same guarantee for the synchronous client."""
    client = ecactus.Ecos(url=hostile_url(mock_server, scenario), access_token="token")
    with pytest.raises(ValidationError):
        client.get_fault_events("device", *EVENT_PERIOD)


@pytest.mark.parametrize(("scenario", "method", "args"), LIST_METHODS)
async def test_async_list_error_hides_input(mock_server, scenario, method, args):
    """The ValidationError of a list endpoint does not quote the data received.

    The models keep their input out of error messages; a list is validated by
    an adapter, the root of that validation, which has to carry the same setting.
    """
    client = ecactus.AsyncEcos(
        url=hostile_url(mock_server, scenario), access_token="token"
    )
    with pytest.raises(ValidationError) as exc_info:
        await getattr(client, method)(*args)
    assert "input_value" not in str(exc_info.value)


@pytest.mark.parametrize(("scenario", "method", "args"), LIST_METHODS)
def test_sync_list_error_hides_input(mock_server, scenario, method, args):
    """Same guarantee for the synchronous client."""
    client = ecactus.Ecos(url=hostile_url(mock_server, scenario), access_token="token")
    with pytest.raises(ValidationError) as exc_info:
        getattr(client, method)(*args)
    assert "input_value" not in str(exc_info.value)
