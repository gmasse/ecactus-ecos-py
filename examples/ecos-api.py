# ruff: noqa: INP001
"""Demonstration usage of the Ecos class."""

from datetime import datetime
import getpass
import logging
from zoneinfo import ZoneInfo

from ecactus import Ecos

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

DATACENTER: str = "EU"

ACCESS_TOKEN: str | None = None
REFRESH_TOKEN: str | None = None
EMAIL: str | None = None
PASSWORD: str | None = None



def main() -> None:
    """Demonstrate the usage of the Ecos class by performing the following steps.

    1. Initializes the Ecos session with an access token or by logging in with email and password.
    2. Retrieves user information from the session.
    3. Lists all devices associated with the user.
    4. Retrieves insight data for each device, including home energy consumption.

    """
    if ACCESS_TOKEN is not None:
        session = Ecos(datacenter=DATACENTER, access_token=ACCESS_TOKEN)
    else:
        session = Ecos(datacenter=DATACENTER)
        email = EMAIL if EMAIL is not None else input("Enter email: ")
        password = (
            PASSWORD if PASSWORD is not None else getpass.getpass("Enter password: ")
        )
        session.login(email, password)

    user_info = session.get_user_info()
    print(user_info) # noqa: T201

    # homes = session.get_homes()
    # print(homes) # noqa: T201

    # print(session.get_realtime_home_data(1876350461905473536)) # noqa: T201

    # print(session.get_devices(1876350461905473536)) # noqa: T201
    # print(session.get_all_devices()) # noqa: T201

    start_date = datetime(
        2024, 11, 20, 10, 0, 0, tzinfo=ZoneInfo(user_info["timezoneName"])
    )
    devices = session.get_all_devices()
    print(devices) # noqa: T201
    for device in devices:
        # print(device) # noqa: T201
        # print(session.get_realtime_device_data(device['deviceId'])) # noqa: T201

        # history = session.get_history(device['deviceId'], start_date, period_type=4)
        # print(history) # noqa: T201
        # for ts, value in history['homeEnergyDps'].items():
        #    time = datetime.fromtimestamp(int(ts))
        #    print(f"{time}: {value}") # noqa: T201

        insight = session.get_insight(
            int(device["deviceId"]), start_date, period_type=5
        )
        print(insight) # noqa: T201
        # for ts, value in insight['deviceRealtimeDto']['solarPowerDps'].items():
        for ts, value in insight["insightConsumptionDataDto"]["homeEnergyDps"].items():
            time = datetime.fromtimestamp(int(ts))
            print(f"{time}: {value}") # noqa: T201

if __name__ == "__main__":
    main()
