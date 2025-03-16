"""Common to all tests."""

import pytest
from pytest_asyncio import is_async_test

from .mock_server import EcosMockServer  # noqa: TID251

LOGIN = "test@test.com"
PASSWORD = "password"


def pytest_collection_modifyitems(items) -> None:
    """Run all test in the same event loop.

    https://pytest-asyncio.readthedocs.io/en/latest/how-to-guides/run_class_tests_in_same_loop.html
    """
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


def run_server(runner, host="127.0.0.1", port=8080):
    """Run the server."""
    import asyncio

    from aiohttp import web

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
    import threading

    from aiohttp import web

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


# @pytest.fixture(autouse=True, scope="session")
# async def async_mock_server():
#     """Start a mock server and return it."""
#     localhost = "127.0.0.1"
#     # Find an unused localhost port from 1024-65535 and return it.
#     import contextlib
#     import socket

#     with contextlib.closing(socket.socket(type=socket.SOCK_STREAM)) as sock:
#         sock.bind((localhost, 0))
#         unused_tcp_port = sock.getsockname()[1]
#     server = EcosMockServer(
#         host=localhost, port=unused_tcp_port, login=LOGIN, password=PASSWORD
#     )
#     await server.start()
#     yield server
#     await server.stop()
