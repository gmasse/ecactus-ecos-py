# ruff: noqa: INP001
"""Demonstration usage of the Async Ecos class."""

import asyncio
from datetime import datetime
import getpass
import logging
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent / "../src"))
from ecactus import AsyncEcos

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

DATACENTER: str = "EU"

ACCESS_TOKEN: str | None = None
REFRESH_TOKEN: str | None = None
EMAIL: str | None = None
PASSWORD: str | None = None

# EMAIL = "name@domain.com"
# PASSWORD = "password"


def get_env() -> None:
    """Get ENV variables and set constant values."""
    global ACCESS_TOKEN, REFRESH_TOKEN, EMAIL, PASSWORD, DATACENTER  # noqa: PLW0603
    ACCESS_TOKEN = os.getenv("ECOS_ACCESS_TOKEN") or ACCESS_TOKEN
    REFRESH_TOKEN = os.getenv("ECOS_REFRESH_TOKEN") or REFRESH_TOKEN
    EMAIL = os.getenv("ECOS_EMAIL") or EMAIL
    PASSWORD = os.getenv("ECOS_PASSWORD") or PASSWORD
    DATACENTER = os.getenv("ECOS_DATACENTER") or DATACENTER


async def main() -> None:
    """Demonstrate the usage of the async Ecos class by performing the following steps.

    1. Initializes the Ecos session with an access token or by logging in with email and password.
    2. Retrieves user information from the session.
    """

    get_env()

    if ACCESS_TOKEN is not None:
        session = AsyncEcos(datacenter=DATACENTER, access_token=ACCESS_TOKEN)
    else:
        email = EMAIL if EMAIL is not None else input("Enter email: ")
        password = (
            PASSWORD if PASSWORD is not None else getpass.getpass("Enter password: ")
        )
        session = AsyncEcos(datacenter=DATACENTER, email=email, password=password)
        # await session.login()

    print(session.access_token)  # noqa: T201
    user = await session.get_user()
    print(user)  # noqa: T201

    homes = await session.get_homes()
    print(homes)  # noqa: T201

    start_date = datetime(2025, 1, 20, 10, 0, 0, tzinfo=ZoneInfo(user.timezone_name))

    for home in homes:
        if home.device_number > 0:

            #print(await session.get_realtime_home_data(home.id))  # noqa: T201

            devices = await session.get_devices(home.id)
            #print(devices)  # noqa: T201
            for device in devices:
                print(device) # noqa: T201
                #print(await session.get_today_device_data(device.id))  # noqa: T201
                #print(await session.get_history(device.id, period_type=1))  # noqa: T201
                print(await session.get_insight(device.id, period_type=5, start_date=start_date))  # noqa: T201

    #print(await session.get_all_devices())  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
