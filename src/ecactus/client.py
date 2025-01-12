"""Implementation of a class for interacting with the ECOS API."""

from datetime import datetime
import logging
import time
from typing import Any, TypeAlias

import requests

# Configure logging
# import http
# http.client.HTTPConnection.debuglevel = 1
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for development; INFO or WARNING for production.


class Ecos:
    """ECOS API client class.

    This class provides methods for interacting with the ECOS API, including
    authentication, retrieving user information, and managing homes. It uses
    the `requests` library to make HTTP requests to the API.

    Attributes:
        access_token (str): The access token for authentication with the ECOS API.
        refresh_token (str): The refresh token for authentication with the ECOS API.
        url (str): The URL of the ECOS API.

    """

    JSON: TypeAlias = Any

    def __init__(
        self,
        datacenter: str | None = None,
        url: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Initialize a session with ECOS API.

        Args:
            datacenter (Optional[str]): The location of the ECOS API datacenter.
                Can be one of 'CN', 'EU', or 'AU'. If not specified and 'url' is not provided,
                a ValueError is raised.
            url (Optional[str]): The URL of the ECOS API. If specified, 'datacenter' is ignored.
            access_token (Optional[str]): The access token for authentication with the ECOS API.
            refresh_token (Optional[str]): The refresh token for authentication with the ECOS API.

        Raises:
            ValueError: If 'datacenter' is not one of 'CN', 'EU', or 'AU' and 'url' is not provided.

        """
        logger.info("Initializing session")
        self.access_token = access_token
        self.refresh_token = refresh_token
        # TODO: get datacenters from https://dcdn-config.weiheng-tech.com/prod/config.json
        datacenters = {
            "CN": "https://api-ecos-hu.weiheng-tech.com",
            "EU": "https://api-ecos-eu.weiheng-tech.com",
            "AU": "https://api-ecos-au.weiheng-tech.com",
        }
        if url is None:
            if datacenter is None:
                raise ValueError("url or datacenter not specified")
            if datacenter not in datacenters:
                raise ValueError(
                    "datacenter must be one of {}".format(", ".join(datacenters.keys()))
                )
            self.url = datacenters[datacenter]
        else:  # url specified, ignore datacenter
            self.url = url.rstrip("/")  # remove trailing / from url

    def _get(self, api_path: str, payload: dict[str, Any] = {}) -> JSON:
        """Make a GET request to the ECOS API.

        Args:
            api_path (str): The path of the API endpoint.
            payload (dict): The data to be sent with the request.

        Returns:
            JSON: The data returned by the API.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error.
            ValueError: If the API returns a non-successful response.

        """
        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.debug("API GET call: %s", full_url)
        try:
            response = requests.get(
                full_url, params=payload, headers={"Authorization": self.access_token}
            )
            body = response.json()
        except requests.exceptions.JSONDecodeError as err:
            raise ValueError(f'Invalid JSON ({body["code"]} {body["message"]})') from err
        else:
            if not response.ok:
                raise requests.exceptions.HTTPError(
                    f'{response.status_code} {body["message"]}'
                )
            if not body["success"]:
              logger.debug(body)
              raise ValueError(f'API call failed: {body["code"]} {body["message"]}')
        data: Ecos.JSON = body["data"]
        return data

    def _post(self, api_path: str, payload: JSON = {}) -> JSON:
        """Make a POST request to the ECOS API.

        Args:
            api_path (str): The path of the API endpoint.
            payload (JSON): The data to be sent with the request.

        Returns:
            JSON: The data returned by the API.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error.
            ValueError: If the API returns a non-successful response.

        """
        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.debug("API POST call: %s", full_url)
        try:
            response = requests.post(
                full_url, json=payload, headers={"Authorization": self.access_token}
            )
            body = response.json()
        except requests.exceptions.JSONDecodeError as err:
            raise ValueError(f'Invalid JSON ({body["code"]} {body["message"]})') from err
        else:
            if not response.ok:
                raise requests.exceptions.HTTPError(
                    f'{response.status_code} {body["message"]}'
                )
            if not body["success"]:
              logger.debug(body)
              raise ValueError(f'API call failed: {body["code"]} {body["message"]}')
        return body["data"]

    def login(self, email: str, password: str) -> None:
        """Authenticate with the ECOS API using a provided email and password.

        Args:
            email (str): The user's email to use for authentication.
            password (str): The user's password to use for authentication.

        """
        logger.info("Login")
        payload = {
            "_t": int(time.time()),
            "clientType": "BROWSER",
            "clientVersion": "1.0",
            "email": email,
            "password": password,
        }
        data = self._post("/api/client/guide/login", payload=payload)
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]

    def get_user_info(self) -> JSON:
        """Get user details.

        Returns:
            { 'username': 'john.doe@acme.com',
              'nickname': 'JohnD',
              'email': 'john.doe@acme.com',
              'phone': '',
              'timeZoneId': '209',
              'timeZone': 'GMT-05:00',
              'timezoneName': 'America/Toronto',
              'datacenterPhoneCode': 49,
              'datacenter': 'EU',
              'datacenterHost': 'https://api-ecos-eu.weiheng-tech.com' }

        """
        logger.info("Get user info")
        return self._get("/api/client/settings/user/info")

    def get_homes(self) -> JSON:
        """Get a list of homes.

        Returns:
          [
            { 'homeId': '1234567890123456789',
              'homeName': 'SHARED_DEVICES',
              'homeType': 0,
              'longitude': None,
              'latitude': None,
              'homeDeviceNumber': 1,
              'relationType': 1,
              'createTime': 946684800000,
              'updateTime': 946684800000 },
            { 'homeId': '9876543210987654321',
              'homeName': 'My Home',
              'homeType': 1,
              'longitude': None,
              'latitude': None,
              'homeDeviceNumber': 0,
              'relationType': 1,
              'createTime': 946684800000,
              'updateTime': 946684800000 }
          ]

        """
        logger.info("Get home list")
        home_list: list[Any] = self._get("/api/client/v2/home/family/query")
        for (
            home
        ) in home_list:  # force the name of the home for shared devices (homeType=0)
            if home["homeType"] == "0":
                home["homeName"] = "SHARED_DEVICES"
        return home_list

    def get_devices(self, home_id: int) -> JSON:
        """Get a list of devices for a home.

        Args:
            home_id (int): The home ID to get devices for.

        Returns:
          [
            { 'deviceId': '1234567890123456789',
              'deviceAliasName': 'My Device',
              'state': 0,
              'batterySoc': 0.0,
              'batteryPower': 0,
              'socketSwitch': None,
              'chargeStationMode': None,
              'vpp': False,
              'type': 1,
              'deviceSn': 'SHC000000000000001',
              'agentId': '9876543210987654321',
              'lon': 0.0,
              'lat': 0.0,
              'deviceType': 'XX-XXX123       ',
              'resourceSeriesId': 101,
              'resourceTypeId': 7,
              'master': 0,
              'emsSoftwareVersion': '000-00000-00',
              'dsp1SoftwareVersion': '111-11111-11' }
            ]

        """
        logger.info("Get devices for home %d", home_id)
        # /api/client/v2/home/device/query?homeId=1876350461905473536
        # return self._get('/api/client/v2/home/device/query')
        return self._get(
            "/api/client/v2/home/device/query", payload={"homeId": home_id}
        )

    def get_all_devices(self) -> JSON:
        """Get a list of devices.

        Returns:
          [
            { 'deviceId': '1234567890123456789',
              'deviceAliasName': 'My Device',
              'wifiSn': 'azerty123456789azertyu',
              'state': 0,
              'weight': 0,
              'temp': None,
              'icon': None,
              'vpp': False,
              'master': 0,
              'type': 1,
              'deviceSn': 'SHC000000000000001',
              'agentId': '',
              'lon': 0.0,
              'lat': 0.0,
              'category': None,
              'model': None,
              'deviceType': None }
            ]

        """
        logger.info("Get devices for every homes")
        return self._get("/api/client/home/device/list")

    def get_realtime_device_data(self, device_id: int) -> JSON:
        """Get power metrics of the current day until now.

        Args:
            device_id (int): The device ID to get power metrics for.

        Returns:
          { 'solarPowerDps':
            { '946685100': 0.0,
              '946685400': 0.0,
              ...
              '946733700': 0.0 },
            'batteryPowerDps': { ... },
            'gridPowerDps': { ... },
            'meterPowerDps': { ... },
            'homePowerDps': { ... },
            'epsPowerDps': { ... } }

        """
        logger.info("Get current day data for device %d", device_id)
        return self._post(
            "/api/client/home/now/device/realtime", payload={"deviceId": device_id}
        )

    def get_realtime_home_data(self, home_id: int) -> JSON:
        """Get current power for the home.

        Args:
            home_id (int): The home ID to get current power for.

        Returns:
          { 'batteryPower': 0,
            'epsPower': 0,
            'gridPower': 23,
            'homePower': 1118,
            'meterPower': 1118,
            'solarPower': 0,
            'chargePower': 0,
            'batterySocList': [
              { 'deviceSn': 'SHC000000000000001',
                'batterySoc': 0.0,
                'sysRunMode': 1,
                'isExistSolar': True,
                'sysPowerConfig': 3 }
            ] }

        """
        logger.info("Get realtime data for home %d", home_id)
        return self._get(
            "/api/client/v2/home/device/runData", payload={"homeId": home_id}
        )

    def get_history(
        self, device_id: int, start_date: datetime, period_type: int
    ) -> JSON:
        """Get aggregated energy for a period.

        Args:
            device_id (int): The device ID to get history for.
            start_date (datetime): The start date.
            period_type (int):
                0 = daily value of the calendar month corresponding to start_date
                1 = daily values of the 4 last days from today (start_date is ignored)
                2 = daily values of the current month (start_date is ignored)
                3 = same than 2 ?
                4 = total for the current month (start_date is ignored)

        Returns:
          { 'energyConsumption': 1221.2,
            'solarPercent': 47.0,
            'homeEnergyDps':
              { '1733112000': 39.6,
                '1733198400': 68.1,
                '1733284800': 75.3,
                ...
                '1735707599': 41.3 } }

        """
        logger.info("Get history for device %d", device_id)
        start_ts = int(start_date.timestamp())
        return self._post(
            "/api/client/home/history/home",
            payload={
                "deviceId": device_id,
                "timestamp": start_ts,
                "periodType": period_type,
            },
        )

    def get_insight(
        self, device_id: int, start_date: datetime, period_type: int
    ) -> JSON:
        """Get energy metrics and statistics of a device for a period.

        Args:
            device_id (int): The device ID to get data for.
            start_date (datetime): The start date.
            period_type (int):
                0 = 5-minute power measurement for the calendar day corresponding to start_date (insightConsumptionDataDto is None)
                1 (not implemented)
                2 = daily energy for the calendar month corresponding to start_date (deviceRealtimeDto is None)
                3 (not implemented)
                4 = monthly energy for the calendar year corresponding to start_date (deviceRealtimeDto is None)
                5 = yearly energy, start_date is ignored? (deviceRealtimeDto is None)

        Returns:
          { 'selfPowered': 0,
            'deviceRealtimeDto':
              { 'solarPowerDps':
                { '1732129500': 0.0,
                  '1732129800': 0.0,
                  ...
                  '1732132800': 0.0 },
                'batteryPowerDps': { ... },
                'gridPowerDps': { ... },
                'meterPowerDps': { ... },
                'homePowerDps': { ... },
                'epsPowerDps': { ... } },
            'deviceStatisticsDto':
              { 'consumptionEnergy': 0.0,
                'fromBattery': 0.0,
                'toBattery': 0.0,
                'fromGrid': 0.0,
                'toGrid': 0.0,
                'fromSolar': 0.0,
                'eps': 0.0 },
            'insightConsumptionDataDto':
              { 'fromBatteryDps':
                { '1733976000': 0.0,
                  '1733889600': 0.0,
                  ...
                  '1734062400': 0.0 },
                'toBatteryDps': { ... },
                'fromGridDps': { ... },
                'toGridDps': { ... },
                'fromSolarDps': { ... },
                'homeEnergyDps': { ... },
                'epsDps': { ... },
                'selfPoweredDps': { ... } } }

        """
        logger.info("Get insight for device %d", device_id)
        start_ts = int(start_date.timestamp() * 1000)  # timestamp in milliseconds
        return self._post(
            "/api/client/v2/device/three/device/insight",
            payload={
                "deviceId": device_id,
                "timestamp": start_ts,
                "periodType": period_type,
            },
        )

"""
API

https://api-ecos-eu.weiheng-tech.com/api/client/v2/home/device/energy?homeId=1870968563368726528
-->
  "data": {
    "today": 1,
    "lastWeekTotalSolar": 125.7,
    "lastWeekTotalGrid": 145.1,
    "lastWeekTotalCarbonEmissions": 125.326,
    "lastWeekTotalSaveStandardCoal": 50.78,
    "weekEnergy": {
      "1": {
        "solarEnergy": 12.9,
        "gridEnergy": 3.8,
        "toGrid": 6.9,
        "homeEnergy": 9.8,
        "selfPowered": 61
      },
      "2": {
        "solarEnergy": 17.7,
        "gridEnergy": 29.6,
        "toGrid": 6.5,
        "homeEnergy": 40.8,
        "selfPowered": 27
      },
      "3": {
        "solarEnergy": 21.3,
        "gridEnergy": 18.9,
        "toGrid": 9,
        "homeEnergy": 31.2,
        "selfPowered": 39
      },
      "4": {
        "solarEnergy": 15.3,
        "gridEnergy": 19.8,
        "toGrid": 4.3,
        "homeEnergy": 30.8,
        "selfPowered": 36
      },
      "5": {
        "solarEnergy": 20.8,
        "gridEnergy": 17.4,
        "toGrid": 10.1,
        "homeEnergy": 28.1,
        "selfPowered": 38
      },
      "6": {
        "solarEnergy": 20.5,
        "gridEnergy": 22.3,
        "toGrid": 3.5,
        "homeEnergy": 39.3,
        "selfPowered": 43
      },
      "7": {
        "solarEnergy": 17.2,
        "gridEnergy": 33.3,
        "toGrid": 5.7,
        "homeEnergy": 44.8,
        "selfPowered": 26
      }
    },
    "carbonEmissionsWeekEnergy": {
      "1": {
        "carbonEmissions": 12.861
      },
      "2": {
        "carbonEmissions": 17.647
      },
      "3": {
        "carbonEmissions": 21.238
      },
      "4": {
        "carbonEmissions": 15.255
      },
      "5": {
        "carbonEmissions": 20.738
      },
      "6": {
        "carbonEmissions": 20.438
      },
      "7": {
        "carbonEmissions": 17.149
      }
    },
    "saveStandardCoalWeekEnergy": {
      "1": {
        "saveStandardCoal": 5.212
      },
      "2": {
        "saveStandardCoal": 7.15
      },
      "3": {
        "saveStandardCoal": 8.605
      },
      "4": {
        "saveStandardCoal": 6.181
      },
      "5": {
        "saveStandardCoal": 8.402
      },
      "6": {
        "saveStandardCoal": 8.282
      },
      "7": {
        "saveStandardCoal": 6.948
      }
    }
  }

https://api-ecos-eu.weiheng-tech.com/api/client/v2/home/device/incrRefresh
{
  "homeId": "1870968563368726528"
}
-->
{
  "code": 0,
  "message": "success",
  "success": true
}
"""
