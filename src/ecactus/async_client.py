"""Implementation of an asynchronous class for interacting with the ECOS API."""

from datetime import datetime
import logging
import time
from typing import Any

from .base import JSON, _BaseEcos
from .exceptions import (
    ApiResponseError,
    AuthenticationError,
    HomeDoesNotExistError,
    ParameterVerificationFailedError,
    UnauthorizedDeviceError,
)

# Configure logging
logger = logging.getLogger(__name__)

class AsyncEcos(_BaseEcos):
    """Asynchronous ECOS API client class.

    This class provides methods for interacting with the ECOS API, including
    authentication, retrieving user information, and managing homes. It uses
    the `aiohttp` library to make asynchronous HTTP requests to the API.
    """

    async def login(self, email: str, password: str) -> None:
        """Authenticate with the ECOS API using a provided email and password.

        Args:
            email: The user's email to use for authentication.
            password: The user's password to use for authentication.

        Raises:
            AuthenticationError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Login")
        payload = {
            "_t": int(time.time()),
            "clientType": "BROWSER",
            "clientVersion": "1.0",
            "email": email,
            "password": password,
        }
        try:
            data = await self._async_post("/api/client/guide/login", payload=payload)
        except ApiResponseError as err:
            if err.code == 20414:
                raise AuthenticationError from err
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]

    async def get_user_info(self) -> JSON:
        """Get user details.

        Returns:
            Details concerning the user. Example:
                ``` py
                {
                    "username": "john.doe@acme.com",
                    "nickname": "JohnD",
                    "email": "john.doe@acme.com",
                    "phone": "",
                    "timeZoneId": "209",
                    "timeZone": "GMT-05:00",
                    "timezoneName": "America/Toronto",
                    "datacenterPhoneCode": 49,
                    "datacenter": "EU",
                    "datacenterHost": "https://api-ecos-eu.weiheng-tech.com"
                }
                ```

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get user info")
        return await self._async_get("/api/client/settings/user/info")

    async def get_homes(self) -> JSON:
        """Get a list of homes.

        Returns:
            A list of homes. Example:
                ``` py
                [
                    {
                        "homeId": "1234567890123456789",
                        "homeName": "SHARED_DEVICES",
                        "homeType": 0,
                        "longitude": None,
                        "latitude": None,
                        "homeDeviceNumber": 1,
                        "relationType": 1,
                        "createTime": 946684800000,
                        "updateTime": 946684800000,
                    },
                    {
                        "homeId": "9876543210987654321",
                        "homeName": "My Home",
                        "homeType": 1,
                        "longitude": None,
                        "latitude": None,
                        "homeDeviceNumber": 0,
                        "relationType": 1,
                        "createTime": 946684800000,
                        "updateTime": 946684800000,
                    },
                ]
                ```

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get home list")
        home_list: list[Any] = await self._async_get("/api/client/v2/home/family/query")
        for (
            home
        ) in home_list:  # force the name of the home for shared devices (homeType=0)
            if int(home["homeType"]) == 0:
                home["homeName"] = "SHARED_DEVICES"
        return home_list

    async def get_devices(self, home_id: str) -> JSON:
        """Get a list of devices for a home.

        Args:
            home_id: The home ID to get devices for.

        Returns:
            A list of devices. Example:
                ``` py
                [
                    {
                        "deviceId": "1234567890123456789",
                        "deviceAliasName": "My Device",
                        "state": 0,
                        "batterySoc": 0.0,
                        "batteryPower": 0,
                        "socketSwitch": None,
                        "chargeStationMode": None,
                        "vpp": False,
                        "type": 1,
                        "deviceSn": "SHC000000000000001",
                        "agentId": "9876543210987654321",
                        "lon": 0.0,
                        "lat": 0.0,
                        "deviceType": "XX-XXX123       ",
                        "resourceSeriesId": 101,
                        "resourceTypeId": 7,
                        "master": 0,
                        "emsSoftwareVersion": "000-00000-00",
                        "dsp1SoftwareVersion": "111-11111-11",
                    },
                ]
                ```

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get devices for home %s", home_id)
        try:
            return await self._async_get(
                "/api/client/v2/home/device/query", payload={"homeId": home_id}
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err

    async def get_all_devices(self) -> JSON:
        """Get a list of all the devices.

        Returns:
            A list of devices. Example:
                ``` py
                [
                    {
                        "deviceId": "1234567890123456789",
                        "deviceAliasName": "My Device",
                        "wifiSn": "azerty123456789azertyu",
                        "state": 0,
                        "weight": 0,
                        "temp": None,
                        "icon": None,
                        "vpp": False,
                        "master": 0,
                        "type": 1,
                        "deviceSn": "SHC000000000000001",
                        "agentId": "",
                        "lon": 0.0,
                        "lat": 0.0,
                        "category": None,
                        "model": None,
                        "deviceType": None,
                    },
                ]
                ```

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get devices for every homes")
        return await self._async_get("/api/client/home/device/list")

    async def get_today_device_data(self, device_id: str) -> JSON:
        """Get power metrics of the current day until now.

        Args:
            device_id: The device ID to get power metrics for.

        Returns:
            Multiple metrics of the current day. Example:
                ``` py
                {
                    "solarPowerDps": {
                        "946685100": 0.0,
                        "946685400": 0.0,
                        ...
                        "946733700": 0.0,
                    },
                    "batteryPowerDps": {...},
                    "gridPowerDps": {...},
                    "meterPowerDps": {...},
                    "homePowerDps": {...},
                    "epsPowerDps": {...},
                }
                ```

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get current day data for device %s", device_id)
        try:
            return await self._async_post(
                "/api/client/home/now/device/realtime", payload={"deviceId": device_id}
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err

    async def get_realtime_home_data(self, home_id: str) -> JSON:
        """Get current power for the home.

        Args:
            home_id: The home ID to get current power for.

        Returns:
            Power data. Example:
                ``` py
                {
                    "batteryPower": 0,
                    "epsPower": 0,
                    "gridPower": 23,
                    "homePower": 1118,
                    "meterPower": 1118,
                    "solarPower": 0,
                    "chargePower": 0,
                    "batterySocList": [
                        {
                            "deviceSn": "SHC000000000000001",
                            "batterySoc": 0.0,
                            "sysRunMode": 1,
                            "isExistSolar": True,
                            "sysPowerConfig": 3,
                        }
                    ],
                }
                ```

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get realtime data for home %s", home_id)
        try:
            return await self._async_get(
                "/api/client/v2/home/device/runData", payload={"homeId": home_id}
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err

    async def get_realtime_device_data(self, device_id: str) -> JSON:
        """Get current power for a device.

        Args:
            device_id: The device ID to get current power for.

        Returns:
            Power data. Example (without solar production):
                ``` py
                {
                    "batterySoc": 0,
                    "batteryPower": 0,
                    "epsPower": 0,
                    "gridPower": 0,
                    "homePower": 3581,
                    "meterPower": 3581,
                    "solarPower": 0,
                    "sysRunMode": 0,
                    "isExistSolar": true,
                    "sysPowerConfig": 3,
                }
                ```
                Example when all solar production is used by home:
                ``` py
                {'batterySoc': 0.0, 'batteryPower': 0, 'epsPower': 0, 'gridPower': 2479, 'homePower': 3674, 'meterPower': 1102, 'solarPower': 2572, 'sysRunMode': 1, 'isExistSolar': True, 'sysPowerConfig': 3}
                # Home 3674 (homePower)
                # PV -> Home 2572 (solarPower)
                # Grid -> Home 1102 (meterPower)
                # gridPower (could be related to operating mode with % reserved SOC for grid connection)
                ```
                Example when solar over production is injected to the grid:
                ``` py
                {'batterySoc': 0.0, 'batteryPower': 0, 'epsPower': 0, 'gridPower': 4194, 'homePower': 3798, 'meterPower': -650, 'solarPower': 4448, 'sysRunMode': 1, 'isExistSolar': True, 'sysPowerConfig': 3}
                # Home 3798
                # PV -> Home 4448
                # Home -> Grid 650
                # gridPower (could be related to operating mode with % reserved SOC for grid connection)
                ```

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get realtime data for device %s", device_id)
        try:
            return await self._async_post(
                "/api/client/home/now/device/runData", payload={"deviceId": device_id}
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err

    async def get_history(
        self, device_id: str, start_date: datetime, period_type: int
    ) -> JSON:
        """Get aggregated energy for a period.

        Args:
            device_id: The device ID to get history for.
            start_date: The start date.
            period_type: Possible value:

                - `0`: daily values of the calendar month corresponding to `start_date`
                - `1`: today daily values (`start_date` is ignored) (?)
                - `2`: daily values of the current month (`start_date` is ignored)
                - `3`: same than 2 ?
                - `4`: total for the current month (`start_date` is ignored)

        Returns:
            Data and metrics corresponding to the defined period. Example:
                ``` py
                {
                    "energyConsumption": 1221.2,
                    "solarPercent": 47.0,
                    "homeEnergyDps": {
                        "1733112000": 39.6,
                        "1733198400": 68.1,
                        "1733284800": 75.3,
                        ...
                        "1735707599": 41.3,
                    },
                }
                ```

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            ParameterVerificationFailedError: If a parameter is not valid (`period_type` number for example)
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get history for device %s", device_id)
        start_ts = int(start_date.timestamp())
        try:
            return await self._async_post(
                "/api/client/home/history/home",
                payload={
                    "deviceId": device_id,
                    "timestamp": start_ts,
                    "periodType": period_type,
                },
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            if err.code == 20404:
                raise ParameterVerificationFailedError from err

    async def get_insight(
        self, device_id: str, start_date: datetime, period_type: int
    ) -> JSON:
        """Get energy metrics and statistics of a device for a period.

        Args:
            device_id: The device ID to get data for.
            start_date: The start date.
            period_type: Possible value:

                - `0`: 5-minute power measurement for the calendar day corresponding to `start_date` (`insightConsumptionDataDto` is `None`)
                - `1`: (not implemented)
                - `2`: daily energy for the calendar month corresponding to `start_date` (`deviceRealtimeDto` is `None`)
                - `3`: (not implemented)
                - `4`: monthly energy for the calendar year corresponding to `start_date` (`deviceRealtimeDto` is `None`)
                - `5`: yearly energy, `start_date` is ignored (?) (`deviceRealtimeDto` is `None`)

        Returns:
            Statistics and metrics corresponding to the defined period. Example:
                ``` py
                {
                    "selfPowered": 0,
                    "deviceRealtimeDto": {
                        "solarPowerDps": {
                            "1732129500": 0.0,
                            "1732129800": 0.0,
                            ...
                            "1732132800": 0.0,
                        },
                        "batteryPowerDps": {...},
                        "gridPowerDps": {...},
                        "meterPowerDps": {...},
                        "homePowerDps": {...},
                        "epsPowerDps": {...},
                    },
                    "deviceStatisticsDto": {
                        "consumptionEnergy": 0.0,
                        "fromBattery": 0.0,
                        "toBattery": 0.0,
                        "fromGrid": 0.0,
                        "toGrid": 0.0,
                        "fromSolar": 0.0,
                        "eps": 0.0,
                    },
                    "insightConsumptionDataDto": {
                        "fromBatteryDps": {
                            "1733976000": 0.0,
                            "1733889600": 0.0,
                            ...
                            "1734062400": 0.0,
                        },
                        "toBatteryDps": {...},
                        "fromGridDps": {...},
                        "toGridDps": {...},
                        "fromSolarDps": {...},
                        "homeEnergyDps": {...},
                        "epsDps": {...},
                        "selfPoweredDps": {...},
                    },
                }
                ```

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            ParameterVerificationFailedError: If a parameter is not valid (`period_type` number for example)
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get insight for device %s", device_id)
        start_ts = int(start_date.timestamp() * 1000)  # timestamp in milliseconds
        try:
            return await self._async_post(
                "/api/client/v2/device/three/device/insight",
                payload={
                    "deviceId": device_id,
                    "timestamp": start_ts,
                    "periodType": period_type,
                },
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            if err.code == 20404:
                raise ParameterVerificationFailedError from err
