# ruff: noqa: INP001
"""Demonstration usage of the Async Ecos class."""

import asyncio
import getpass
import logging

from ecactus import AsyncEcos

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

DATACENTER: str = "EU"

ACCESS_TOKEN: str | None = None
REFRESH_TOKEN: str | None = None
EMAIL: str | None = None
PASSWORD: str | None = None

#EMAIL = "name@domain.com"
#PASSWORD = "password"

async def main() -> None:
    """Demonstrate the usage of the async Ecos class by performing the following steps.

    1. Initializes the Ecos session with an access token or by logging in with email and password.
    2. Retrieves user information from the session.
    """
    if ACCESS_TOKEN is not None:
        session = AsyncEcos(datacenter=DATACENTER, access_token=ACCESS_TOKEN)
    else:
        session = AsyncEcos(datacenter=DATACENTER)
        email = EMAIL if EMAIL is not None else input("Enter email: ")
        password = (
            PASSWORD if PASSWORD is not None else getpass.getpass("Enter password: ")
        )
        await session.login(email, password)

    print(session.access_token) # noqa: T201
    user_info = await session.get_user_info()
    print(user_info) # noqa: T201

if __name__ == "__main__":
    asyncio.run(main())
