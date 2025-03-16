"""Unit tests for synchronous Ecos class."""

from datetime import datetime, timedelta
import logging

import pytest

import ecactus
from ecactus.exceptions import (
    AuthenticationError,
    HomeDoesNotExistError,
    HttpError,
    InitializationError,
    InvalidJsonError,
    ParameterVerificationFailedError,
    UnauthorizedDeviceError,
    UnauthorizedError,
)

from .conftest import LOGIN, PASSWORD  # noqa: TID251

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


@pytest.fixture(scope="session")
def client(mock_server):
    """Return an ECOS client."""
    return ecactus.Ecos(url=mock_server.url)


@pytest.fixture(scope="session")
def bad_client(mock_server):
    """Return an ECOS client with wrong authentication token."""
    return ecactus.Ecos(url=mock_server.url, access_token="wrong_token")


def test_exceptions():
    """Test exceptions."""
    exc = InitializationError()
    assert str(exc) == "Initialization error"
    exc = AuthenticationError()
    assert str(exc) == "Account or password or country error"
    exc = UnauthorizedError()
    assert str(exc) == "Unauthorized"
    exc = HomeDoesNotExistError()
    assert str(exc) == "Home does not exist"
    exc = HomeDoesNotExistError("home_id")
    assert str(exc) == "Home does not exist: home_id"
    exc = UnauthorizedDeviceError()
    assert str(exc) == "Device is not authorized"
    exc = ParameterVerificationFailedError()
    assert str(exc) == "Parameter verification failed"
    exc = InvalidJsonError()
    assert str(exc) == "Invalid JSON"
    exc = HttpError(404, "Not Found")
    assert str(exc) == "HTTP error: 404 Not Found"


def test_client():
    """Test ECOS client."""
    with pytest.raises(InitializationError):
        ecactus.Ecos()
    with pytest.raises(InitializationError):
        ecactus.Ecos(datacenter="XX")
    client = ecactus.Ecos(datacenter="EU")
    assert "weiheng-tech.com" in client.url


def test_ensure_login(mock_server):
    """Test autologin."""
    temp_client = ecactus.Ecos(url=mock_server.url)
    with pytest.raises(AuthenticationError) as excinfo:
        user = temp_client.get_user()
    assert str(excinfo.value) == "Missing Account or Password"
    temp_client = ecactus.Ecos(email=LOGIN, password=PASSWORD, url=mock_server.url)
    user = temp_client.get_user()
    assert user.username == LOGIN


def test_login(mock_server, client):
    """Test login."""
    with pytest.raises(AuthenticationError):
        client.login("wrong_login", "wrong_password")
    client.login(LOGIN, PASSWORD)
    assert client.access_token == mock_server.access_token
    assert client.refresh_token == mock_server.refresh_token


def test_get_user(client, bad_client):
    """Test get user info."""
    with pytest.raises(UnauthorizedError):
        bad_client.get_user()
    user = client.get_user()
    assert user.username == LOGIN


def test_get_homes(client, bad_client):
    """Test get homes."""
    with pytest.raises(UnauthorizedError):
        bad_client.get_homes()
    homes = client.get_homes()
    assert homes[1].name == "My Home"


def test_get_devices(client, bad_client):
    """Test get devices."""
    with pytest.raises(UnauthorizedError):
        bad_client.get_devices(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        client.get_devices(home_id=0)
    devices = client.get_devices(home_id=9876543210987654321)
    assert devices[0].alias == "My Device"


def test_get_all_devices(client, bad_client):
    """Test get all devices."""
    with pytest.raises(UnauthorizedError):
        bad_client.get_all_devices()
    devices = client.get_all_devices()
    assert devices[0].alias == "My Device"


def test_get_today_device_data(client, bad_client):
    """Test get current day device data."""
    with pytest.raises(UnauthorizedError):
        bad_client.get_today_device_data(device_id=0)
    with pytest.raises(UnauthorizedDeviceError):
        client.get_today_device_data(device_id=0)
    power_ts = client.get_today_device_data(device_id=1234567890123456789)
    assert len(power_ts.metrics) > 0
    # get the first  timestamp
    first_timestamp = power_ts.metrics[0].timestamp
    assert power_ts.find_by_timestamp(first_timestamp, exact=False).solar is not None
    assert power_ts.find_by_timestamp(first_timestamp, exact=True).solar is not None
    # get a timestamp that does not exist
    before_timestamp = first_timestamp - timedelta(seconds=1)
    assert power_ts.find_by_timestamp(before_timestamp, exact=False).solar == power_ts.metrics[0].solar # the nearst metric is returned
    assert power_ts.find_by_timestamp(before_timestamp, exact=True) is None # exact lookup returns None
    # get a timestamp after the last one
    last_timestamp = power_ts.metrics[-1].timestamp
    after_timestamp =  last_timestamp + timedelta(seconds=1)
    assert power_ts.find_by_timestamp(after_timestamp, exact=False).solar == power_ts.metrics[-1].solar # value is 1/10th of the position
    assert power_ts.find_by_timestamp(after_timestamp, exact=True) is None
    # get a timestamp within 2 existings
    if len(power_ts.metrics) > 2:
        timestamp1 = power_ts.metrics[1].timestamp
        timestamp2 = power_ts.metrics[2].timestamp
        delta = timestamp2 - timestamp1
        if delta >= timedelta(seconds=2):
            timestamp = timestamp1 + delta/2
            assert power_ts.find_by_timestamp(timestamp, exact=False).solar == power_ts.metrics[1].solar # returns the value in 2nd position
            timestamp = timestamp1 + delta/2 + timedelta(seconds=1)
            assert power_ts.find_by_timestamp(timestamp, exact=False).solar == power_ts.metrics[2].solar # returns the value in 3rd position
    # return series between 2 dates
    between_ts = power_ts.find_between(first_timestamp, last_timestamp)
    assert len(between_ts.metrics) == len(power_ts.metrics)

def test_get_realtime_device_data(client, bad_client):
    """Test get realtime device data."""
    with pytest.raises(UnauthorizedError):
        bad_client.get_realtime_device_data(device_id=0)
    with pytest.raises(UnauthorizedDeviceError):
        client.get_realtime_device_data(device_id=0)
    power_metrics = client.get_realtime_device_data(device_id=1234567890123456789)
    assert power_metrics.home is not None


def test_get_realtime_home_data(client, bad_client):
    """Test get realtime home data."""
    with pytest.raises(UnauthorizedError):
        bad_client.get_realtime_home_data(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        client.get_realtime_home_data(home_id=0)
    power_metrics = client.get_realtime_home_data(home_id=9876543210987654321)
    assert power_metrics.home is not None


def test_get_history(client, bad_client):
    """Test get history."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        bad_client.get_history(device_id=0, start_date=now, period_type=0)
    with pytest.raises(UnauthorizedDeviceError):
        client.get_history(device_id=0, start_date=now, period_type=0)
    with pytest.raises(ParameterVerificationFailedError):
        client.get_history(
            device_id=1234567890123456789, start_date=now, period_type=5
        )
    history = client.get_history(
        device_id=1234567890123456789, start_date=now, period_type=4
    )
    assert len(history.metrics) == 1

    # TODO other period types


def test_get_insight(client, bad_client):
    """Test get insight."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        bad_client.get_insight(device_id=0, start_date=now, period_type=0)
    with pytest.raises(UnauthorizedDeviceError):
        client.get_insight(device_id=0, start_date=now, period_type=0)
    with pytest.raises(ParameterVerificationFailedError):
        client.get_insight(
            device_id=1234567890123456789, start_date=now, period_type=1
        )
    with pytest.raises(ParameterVerificationFailedError):
        client.get_insight(
            device_id=1234567890123456789, period_type=1
        )
    insight = client.get_insight(
        device_id=1234567890123456789, start_date=now, period_type=0
    )
    assert len(insight.power_timeseries.metrics) > 1
    insight = client.get_insight(
        device_id=1234567890123456789, start_date=now, period_type=2
    )
    assert len(insight.energy_timeseries.metrics) > 1



# TODO test 404
# TODO test bad method (ex GET in place of POST)
