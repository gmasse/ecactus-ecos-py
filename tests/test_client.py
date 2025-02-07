"""Unit tests for synchronous Ecos class."""

import asyncio
from datetime import datetime
import logging
import threading

from aiohttp import web
import pytest

import ecactus

from .mock_server import EcosMockServer  # noqa: TID251

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

LOGIN = "test@test.com"
PASSWORD = "password"


def run_server(runner, host="127.0.0.1", port=8080):
    """Run the server."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, host, port)
    loop.run_until_complete(site.start())
    loop.run_forever()


@pytest.fixture(autouse=True, scope="session")
def mock_server():
    """Start a mock server in a thread and return it."""
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
    server.setup_routes()
    runner = web.AppRunner(server.app)
    thread = threading.Thread(
        target=run_server, args=(runner, server.host, server.port)
    )
    thread.daemon = True  # daeamon thread will be killed when main thread ends
    thread.start()
    server.url = f"http://{server.host}:{server.port}"
    return server


@pytest.fixture(scope="session")
def client(mock_server):
    """Return an ECOS client."""
    return ecactus.Ecos(url=mock_server.url)


def test_login(mock_server, client):
    """Test login."""
    with pytest.raises(ecactus.ApiResponseError):
        client.login("wrong_login", "wrong_password")
    client.login(LOGIN, PASSWORD)
    assert client.access_token == mock_server.access_token
    assert client.refresh_token == mock_server.refresh_token


def test_get_user_info(caplog, mock_server, client):
    """Test get user info."""
    caplog.set_level(logging.DEBUG)
    user_info = client.get_user_info()
    assert user_info["username"] == LOGIN


def test_get_homes(mock_server, client):
    """Test get homes."""
    homes = client.get_homes()
    assert homes[1]["homeName"] == "My Home"


def test_get_devices(mock_server, client):
    """Test get devices."""
    with pytest.raises(ecactus.ApiResponseError) as err:
        client.get_devices(home_id=0)
    assert str(err.getrepr(style="value")) == "API call failed: 20450 Home does not exist."

    devices = client.get_devices(home_id=9876543210987654321)
    assert devices[0]["deviceAliasName"] == "My Device"


def test_get_all_devices(mock_server, client):
    """Test get all devices."""
    devices = client.get_all_devices()
    assert devices[0]["deviceAliasName"] == "My Device"


def test_get_realtime_device_data(mock_server, client):
    """Test get realtime device data."""
    with pytest.raises(ecactus.HttpError) as err:
        client.get_realtime_device_data(device_id=0)
    assert str(err.getrepr(style="value")) == "HTTP error: 401 unauthorized device"

    data = client.get_realtime_device_data(device_id=1234567890123456789)
    assert len(data["solarPowerDps"]) > 0


def test_get_realtime_home_data(mock_server, client):
    """Test get reatime home data."""
    with pytest.raises(ecactus.ApiResponseError) as err:
        client.get_devices(home_id=0)
    assert str(err.getrepr(style="value")) == "API call failed: 20450 Home does not exist."

    data = client.get_realtime_home_data(home_id=9876543210987654321)
    assert data.get("homePower") is not None


async def test_get_history(mock_server, client):
    """Test get history."""
    now = datetime.now()
    with pytest.raises(ecactus.HttpError) as err:
        client.get_history(device_id=0, start_date=now, period_type=0)
    assert str(err.getrepr(style="value")) == "HTTP error: 401 unauthorized device"

    with pytest.raises(ecactus.ApiResponseError) as err:
        client.get_history(device_id=1234567890123456789, start_date=now, period_type=5)
    assert str(err.getrepr(style="value")) == "API call failed: 20424 Parameter verification failed"

    data = client.get_history(device_id=1234567890123456789, start_date=now, period_type=4)
    assert len(data["homeEnergyDps"]) == 1

    #TODO other period types

async def test_get_insight(mock_server, client):
    """Test get insight."""
    now = datetime.now()
    with pytest.raises(ecactus.HttpError) as err:
        client.get_insight(device_id=0, start_date=now, period_type=0)
    assert str(err.getrepr(style="value")) == "HTTP error: 401 unauthorized device"

    with pytest.raises(ecactus.ApiResponseError) as err:
        client.get_insight(device_id=1234567890123456789, start_date=now, period_type=1)
    assert str(err.getrepr(style="value")) == "API call failed: 20404 Parameter verification failed"

    data = client.get_insight(device_id=1234567890123456789, start_date=now, period_type=0)
    assert len(data["deviceRealtimeDto"]["solarPowerDps"]) > 1


# TODO test wrong login payload
# TODO test 404
# TODO test all call not authorized
# TODO test bad method (ex GET in place of POST)
