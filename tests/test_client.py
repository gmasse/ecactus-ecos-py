"""Unit tests for synchronous Ecos class."""

from datetime import datetime
import logging

import pytest

import ecactus
from ecactus.exceptions import (
    AuthenticationError,
    HomeDoesNotExistError,
    InitializationError,
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


def test_client():
    """Test ECOS client."""
    with pytest.raises(InitializationError):
        ecactus.Ecos()
    with pytest.raises(InitializationError):
        ecactus.Ecos(datacenter="XX")
    client = ecactus.Ecos(datacenter="EU")
    assert "weiheng-tech.com" in client.url


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
    insight = client.get_insight(
        device_id=1234567890123456789, start_date=now, period_type=0
    )
    assert len(insight.power_timeseries.metrics) > 1


# TODO test 404
# TODO test bad method (ex GET in place of POST)
