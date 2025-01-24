"""Unit tests for synchronous Ecos class."""

import logging

import pytest

import ecactus

from .mock_server import EcosMockServer  #noqa: TID251

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

LOGIN = 'test@test.com'
PASSWORD = 'password'

@pytest.fixture(autouse=True, scope="session")
async def mock_server():
    """Start a mock server and return it."""
    localhost = '127.0.0.1'
    # Find an unused localhost port from 1024-65535 and return it.
    import contextlib
    import socket
    with contextlib.closing(socket.socket(type=socket.SOCK_STREAM)) as sock:
        sock.bind((localhost, 0))
        unused_tcp_port = sock.getsockname()[1]
    server= EcosMockServer(host=localhost, port=unused_tcp_port, login=LOGIN, password=PASSWORD)
    await server.start()
    yield server
    await server.stop()

@pytest.fixture(scope="session")
async def client(mock_server):
    """Return an ECOS client."""qu
    return ecactus.AsyncEcos(url=mock_server.url)


async def test_login(mock_server, client):
    """Test login."""
    with pytest.raises(ecactus.ApiResponseError):
        await client.login("wrong_login", "wrong_password")
    await client.login(LOGIN, PASSWORD)
    assert client.access_token == mock_server.access_token
    assert client.refresh_token == mock_server.refresh_token
