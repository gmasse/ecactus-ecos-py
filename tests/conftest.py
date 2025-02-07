"""Common to all tests."""

import pytest
from pytest_asyncio import is_async_test


def pytest_collection_modifyitems(items) -> None:
    """Run all test in the same event loop.

    https://pytest-asyncio.readthedocs.io/en/latest/how-to-guides/run_class_tests_in_same_loop.html
    """
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)
