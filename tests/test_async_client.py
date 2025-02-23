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

from .mock_server import EcosMockServer  # noqa: TID251

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

LOGIN = "test@test.com"
PASSWORD = "password"


@pytest.fixture(autouse=True, scope="session")
async def mock_server():
    """Start a mock server and return it."""
    localhost = "127.0.0.1"
    # Find an unused localhost port from 1024-65535 and return it.
    import contextlib
    import socket

    with contextlib.closing(socket.socket(type=socket.SOCK_STREAM)) as sock:
        sock.bind((localhost, 0))
        unused_tcp_port = sock.getsockname()[1]
    server = EcosMockServer(
        host=localhost, port=unused_tcp_port, login=LOGIN, password=PASSWORD
    )
    await server.start()
    yield server
    await server.stop()


@pytest.fixture(scope="session")
async def async_client(mock_server):
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
        ecactus.AsyncEcos(datacenter='XX')
    client = ecactus.AsyncEcos(datacenter='EU')
    assert 'weiheng-tech.com' in client.url


async def test_login(mock_server, async_client):
    """Test login."""
    with pytest.raises(AuthenticationError):
        await async_client.login("wrong_login", "wrong_password")
    await async_client.login(LOGIN, PASSWORD)
    assert async_client.access_token == mock_server.access_token
    assert async_client.refresh_token == mock_server.refresh_token


async def test_get_user_info(mock_server, async_client, bad_client):
    """Test get user info."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_user_info()
    user_info = await async_client.get_user_info()
    assert user_info["username"] == LOGIN


async def test_get_homes(mock_server, async_client, bad_client):
    """Test get homes."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_homes()
    homes = await async_client.get_homes()
    assert homes[1]["homeName"] == "My Home"


async def test_get_devices(mock_server, async_client, bad_client):
    """Test get devices."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_devices(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        await async_client.get_devices(home_id=0)
    devices = await async_client.get_devices(home_id=9876543210987654321)
    assert devices[0]["deviceAliasName"] == "My Device"


async def test_get_all_devices(mock_server, async_client, bad_client):
    """Test get all devices."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_all_devices()
    devices = await async_client.get_all_devices()
    assert devices[0]["deviceAliasName"] == "My Device"


async def test_get_today_device_data(mock_server, async_client, bad_client):
    """Test get current day device data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_today_device_data(device_id=0)
    with pytest.raises(UnauthorizedDeviceError):
        await async_client.get_today_device_data(device_id=0)
    data = await async_client.get_today_device_data(device_id=1234567890123456789)
    assert len(data["solarPowerDps"]) > 0


async def test_get_realtime_device_data(mock_server, async_client, bad_client):
    """Test get realtime device data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_realtime_device_data(device_id=0)
    with pytest.raises(UnauthorizedDeviceError):
        await async_client.get_realtime_device_data(device_id=0)
    data = await async_client.get_realtime_device_data(device_id=1234567890123456789)
    assert data.get("homePower") is not None


async def test_get_realtime_home_data(mock_server, async_client, bad_client):
    """Test get realtime home data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_realtime_home_data(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        await async_client.get_realtime_home_data(home_id=0)
    data = await async_client.get_realtime_home_data(home_id=9876543210987654321)
    assert data.get("homePower") is not None


async def test_get_history(mock_server, async_client, bad_client):
    """Test get history."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        await bad_client.get_history(device_id=0, start_date=now, period_type=0)
    with pytest.raises(UnauthorizedDeviceError):
        await async_client.get_history(device_id=0, start_date=now, period_type=0)
    with pytest.raises(ParameterVerificationFailedError):
        await async_client.get_history(device_id=1234567890123456789, start_date=now, period_type=5)
    data = await async_client.get_history(device_id=1234567890123456789, start_date=now, period_type=4)
    assert len(data["homeEnergyDps"]) == 1

    #TODO other period types


async def test_get_insight(mock_server, async_client, bad_client):
    """Test get insight."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        await bad_client.get_insight(device_id=0, start_date=now, period_type=0)
    with pytest.raises(UnauthorizedDeviceError):
        await async_client.get_insight(device_id=0, start_date=now, period_type=0)
    with pytest.raises(ParameterVerificationFailedError):
        await async_client.get_insight(device_id=1234567890123456789, start_date=now, period_type=1)
    data = await async_client.get_insight(device_id=1234567890123456789, start_date=now, period_type=0)
    assert len(data["deviceRealtimeDto"]["solarPowerDps"]) > 1


# TODO test 404
# TODO test all call not authorized
# TODO test bad method (ex GET in place of POST)
