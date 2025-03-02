"""Unit tests for asynchronous Ecos class."""

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
async def client(mock_server):
    """Return an ECOS client."""
    return ecactus.AsyncEcos(url=mock_server.url)


@pytest.fixture(scope="session")
def bad_client(mock_server):
    """Return an ECOS client with wrong authentication token."""
    return ecactus.AsyncEcos(url=mock_server.url, access_token="wrong_token")


def test_client():
    """Test ECOS client."""
    with pytest.raises(InitializationError):
        ecactus.AsyncEcos()
    with pytest.raises(InitializationError):
        ecactus.AsyncEcos(datacenter="XX")
    client = ecactus.AsyncEcos(datacenter="EU")
    assert "weiheng-tech.com" in client.url


async def test_login(mock_server, client):
    """Test login."""
    with pytest.raises(AuthenticationError):
        await client.login("wrong_login", "wrong_password")
    await client.login(LOGIN, PASSWORD)
    assert client.access_token == mock_server.access_token
    assert client.refresh_token == mock_server.refresh_token


async def test_get_user(client, bad_client):
    """Test get user info."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_user()
    user = await client.get_user()
    assert user.username == LOGIN


async def test_get_homes(client, bad_client):
    """Test get homes."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_homes()
    homes = await client.get_homes()
    assert homes[1].name == "My Home"


async def test_get_devices(client, bad_client):
    """Test get devices."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_devices(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        await client.get_devices(home_id=0)
    devices = await client.get_devices(home_id=9876543210987654321)
    assert devices[0].alias == "My Device"


async def test_get_all_devices(client, bad_client):
    """Test get all devices."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_all_devices()
    devices = await client.get_all_devices()
    assert devices[0].alias == "My Device"


async def test_get_today_device_data(client, bad_client):
    """Test get current day device data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_today_device_data(device_id=0)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_today_device_data(device_id=0)
    power_ts = await client.get_today_device_data(device_id=1234567890123456789)
    assert len(power_ts.metrics) > 0


async def test_get_realtime_device_data(client, bad_client):
    """Test get realtime device data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_realtime_device_data(device_id=0)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_realtime_device_data(device_id=0)
    power_metrics = await client.get_realtime_device_data(device_id=1234567890123456789)
    assert power_metrics.home is not None


async def test_get_realtime_home_data(client, bad_client):
    """Test get realtime home data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_realtime_home_data(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        await client.get_realtime_home_data(home_id=0)
    power_metrics = await client.get_realtime_home_data(home_id=9876543210987654321)
    assert power_metrics.home is not None


async def test_get_history(client, bad_client):
    """Test get history."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        await bad_client.get_history(device_id=0, start_date=now, period_type=0)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_history(device_id=0, start_date=now, period_type=0)
    with pytest.raises(ParameterVerificationFailedError):
        await client.get_history(
            device_id=1234567890123456789, start_date=now, period_type=5
        )
    history = await client.get_history(
        device_id=1234567890123456789, start_date=now, period_type=4
    )
    assert len(history.metrics) == 1

    # TODO other period types


async def test_get_insight(client, bad_client):
    """Test get insight."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        await bad_client.get_insight(device_id=0, start_date=now, period_type=0)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_insight(device_id=0, start_date=now, period_type=0)
    with pytest.raises(ParameterVerificationFailedError):
        await client.get_insight(
            device_id=1234567890123456789, start_date=now, period_type=1
        )
    insight = await client.get_insight(
        device_id=1234567890123456789, start_date=now, period_type=0
    )
    assert len(insight.power_timeseries.metrics) > 1


# TODO test 404
# TODO test bad method (ex GET in place of POST)
