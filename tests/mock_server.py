"""Ecos API mock server."""

import asyncio
from datetime import datetime, timedelta
import logging
import random
import string
from typing import Any

from aiohttp import web
from dateutil.relativedelta import relativedelta
from multidict import CIMultiDictProxy

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

JSON = Any


class EcosMockServer:
    """Ecos API mock server class."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        login: str = "test@test.com",
        password: str = "test",
    ) -> None:
        """Initialize the class."""
        logger.info("Initializing EcosMockServer")
        self.url: str | None = None
        self.host: str = host
        self.port: int = port
        self.login: str = login
        self.password: str = password
        self.app: web.Application = web.Application()
        self._runner: web.AppRunner | None = None
        base_token: str = f"{self._generate_random(string.ascii_letters + string.digits, 20)}.{self._generate_random(string.ascii_letters + string.digits, 155)}"
        self.access_token: str = base_token + self._generate_random(
            string.ascii_letters + string.digits + "-_", 86
        )
        self.refresh_token: str = base_token + self._generate_random(
            string.ascii_letters + string.digits + "-_", 86
        )

    @staticmethod
    def _generate_random(allowed: str, length: int) -> str:
        """Generate a random string of a specified length from a set of allowed characters.

        Args:
            allowed (str): A string of allowed characters.
            length (int): The desired length of the generated random string.

        Returns:
            str: A random string of the specified length, composed of characters from the allowed set.

        Example:
            generate_random(string.ascii_letters + string.digits, 10)

        """
        return "".join(random.choice(allowed) for _ in range(length))

    @staticmethod
    def _response(
        data: JSON = None,
        code: int = 0,
        message: str = "success",
        success: bool = True,
        http_status: int = 200,
    ) -> web.Response:
        output: JSON = {
            "code": code,
            "message": message,
            "success": success,
        }
        if data is not None:
            output["data"] = data
        return web.json_response(output, status=http_status)

    @staticmethod
    def _ok_response(
        data: JSON = None,
        code: int = 0,
        message: str = "success",
        success: bool = True,
    ) -> web.Response:
        return EcosMockServer._response(data, code, message, success, http_status=200)

    @staticmethod
    def _success_response(data: JSON = None) -> web.Response:
        return EcosMockServer._ok_response(
            data, code=0, message="success", success=True
        )

    @staticmethod
    def _unauthorized_response() -> web.Response:
        return EcosMockServer._response(
            code=401, message="Unauthorized", success=False, http_status=401
        )

    @staticmethod
    def _not_implemented_response() -> web.Response:
        return web.HTTPNotImplemented()

    async def handle_login(self, request: web.Request) -> web.Response:
        """Mock login endpoint."""
        output: JSON = {}
        data = await request.json()  # Parse the JSON payload
        if (
            not data.get("clientVersion")
            or data.get("clientType") != "BROWSER"
            or not data.get("email")
            or not data.get("password")
        ):
            output["code"] = 20000
            output["message"] = ""
            output["success"] = False
            output["data"] = {}
            if not data.get("clientVersion"):
                output["message"] = output["data"]["clientVersion"] = "cannot be blank"
            if data.get("clientType") != "BROWSER":
                output["message"] = output["data"]["clientType"] = (
                    "Invalid terminal type"
                )
            if not data.get("email"):
                output["message"] = output["data"]["email"] = "cannot be blank"
            if not data.get("password"):
                output["message"] = output["data"]["password"] = "cannot be blank"
        elif data.get("email") != self.login or data.get("password") != self.password:
            output = {
                "code": 20414,
                "message": "Account or password or country error",
                "success": False,
            }
        else:
            output = {
                "code": 0,
                "message": "success",
                "success": True,
                "data": {
                    "accessToken": self.access_token,
                    "refreshToken": self.refresh_token,
                },
            }
        return web.json_response(output, status=200)

    def _is_authorized_request(self, request: web.Request) -> bool:
        """Check if request is authorized."""
        headers: CIMultiDictProxy[str] = request.headers
        return bool(headers.get("Authorization") == self.access_token)

    async def handle_get_user_info(self, request: web.Request) -> web.Response:
        """Mock user info endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data={
                "username": self.login,
                "nickname": "Test",
                "email": self.login,
                "phone": "",
                "timeZoneId": "209",
                "timeZone": "GMT-05:00",
                "timezoneName": "America/Toronto",
                "datacenterPhoneCode": 49,
                "datacenter": "EU",
                "datacenterHost": "https://api-ecos-eu.weiheng-tech.com",
            }
        )

    async def handle_get_homes(self, request: web.Request) -> web.Response:
        """Mock get homes endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data=[
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
        )

    async def handle_get_devices(self, request: web.Request) -> web.Response:
        """Mock get devices endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        if str(request.query.get("homeId")) != "9876543210987654321":
            return EcosMockServer._ok_response(
                code=20450, message="Home does not exist.", success=False
            )
        return EcosMockServer._success_response(
            data=[
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
                    "bmsVendor": "VENDOR",
                    "firstInstall": 1700000000000,
                    "isMain": None,
                    "safetyStandard": 1,
                    "wifiSn": "WIFI000000000001",
                }
            ]
        )

    async def handle_get_all_devices(self, request: web.Request) -> web.Response:
        """Mock get all devices endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data=[
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
                }
            ]
        )

    @staticmethod
    async def _generate_metrics_data(
        start_date: datetime,
        end_date: datetime,
        interval: timedelta = timedelta(minutes=5),
        timestamp_format: str = "seconds",
    ) -> dict[str, float]:
        """Generate fake metrics data for a given date range."""
        metrics_data: dict[str, float] = {}
        current_date: datetime = start_date
        fake_value: int = 0
        while current_date < end_date:
            fake_value += 1  # increment the fake value
            current_date += interval
            timestamp: int = int(current_date.timestamp())
            if timestamp_format == "milliseconds":
                timestamp *= 1000
            metrics_data[str(timestamp)] = float(fake_value / 10)
        return metrics_data

    async def handle_get_today_device_data(self, request: web.Request) -> web.Response:
        """Mock get today device data endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        request_payload = await request.json()
        logger.debug(request_payload)
        if str(request_payload.get("deviceId")) != "1234567890123456789":
            return EcosMockServer._response(
                code=20424,
                message="unauthorized device",
                success=False,
                http_status=401,
            )
        fake_data: dict[str, float] = await self._generate_metrics_data(
            start_date=datetime.today().replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            end_date=datetime.now(),
        )
        return EcosMockServer._success_response(
            data={
                "solarPowerDps": fake_data,
                "batteryPowerDps": fake_data,
                "gridPowerDps": fake_data,
                "meterPowerDps": fake_data,
                "homePowerDps": fake_data,
                "epsPowerDps": fake_data,
            }
        )

    async def handle_get_realtime_home_data(self, request: web.Request) -> web.Response:
        """Mock get realtime home data endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        if str(request.query.get("homeId")) != "9876543210987654321":
            return EcosMockServer._ok_response(
                code=20450, message="Home does not exist.", success=False
            )
        return EcosMockServer._success_response(
            data={
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
        )

    async def handle_get_realtime_device_data(
        self, request: web.Request
    ) -> web.Response:
        """Mock get realtime device data endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        request_payload = await request.json()
        logger.debug(request_payload)
        if str(request_payload.get("deviceId")) != "1234567890123456789":
            return EcosMockServer._response(
                code=20424,
                message="unauthorized device",
                success=False,
                http_status=401,
            )
        return EcosMockServer._success_response(
            data={
                "batterySoc": 0,
                "batteryPower": 0,
                "epsPower": 0,
                "gridPower": 0,
                "homePower": 3581,
                "meterPower": 3581,
                "solarPower": 0,
                "sysRunMode": 0,
                "isExistSolar": True,
                "sysPowerConfig": 3,
                "batHeaterStatus": 0,
            }
        )

    async def handle_get_device_detail(self, request: web.Request) -> web.Response:
        """Mock three-phase device detail endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data={
                "name": "My Device",
                "deviceSn": "SHC000000000000001",
                "wifiSn": "WIFI000000000001",
                "deviceModel": "XX-XXX123",
                "accountList": [
                    {"accountId": "1", "account": "user@example.com", "master": 1}
                ],
                "master": 1,
                "type": 3,
                "emsSoftwareVersion": "000-00000-00",
                "dsp1SoftwareVersion": "111-11111-11",
                "resourceSeriesId": 102,
                "resourceTypeId": 20,
                "firstInstall": 1700000000000,
                "ratedPower": "10000W",
                "batteryCapacity": "9.98",
                "safetyStandard": 1,
            }
        )

    async def handle_get_device_settings(self, request: web.Request) -> web.Response:
        """Mock device settings endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data={
                "minCapacity": 15,
                "chargeUseMode": 0,
                "maxFeedIn": 50,
                "epsBatteryMin": 10,
                "dischargeToGridFlag": 0,
                "selfSoc": 15,
                "selfEpsBat": 10,
                "selfFeedIn": 50,
                "regularSoc": 15,
                "regularEpsBat": 10,
                "regularFeedIn": 50,
                "backupSoc": -1,
                "backupEpsBat": -1,
                "backupFeedIn": -1,
                "emsSoftwareVersion": "000-00000-00",
                "dsp1SoftwareVersion": "111-11111-11",
                "bmsSoftwareVersion": "222-22222-22",
                "ratedPower": "10000W",
                "region": "",
                "autoStrategy": 0,
                "strategyMode": 0,
                "defChargePower": 10000,
                "defDischargePower": 10000,
                "feedInProhibition": 0,
                "chargingList": [],
                "dischargingList": [],
            }
        )

    async def handle_get_device_modes(self, request: web.Request) -> web.Response:
        """Mock device mode endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data=[
                {
                    "deviceName": "My Device",
                    "chargeUseMode": 0,
                    "isMain": None,
                    "strategyMode": 0,
                }
            ]
        )

    async def handle_get_power_limit(self, request: web.Request) -> web.Response:
        """Mock power limit endpoint (bare number)."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(data=0)

    async def handle_get_forecast(self, request: web.Request) -> web.Response:
        """Mock PV and load forecast endpoints, plain and realtime."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        day_ms = int(request.query.get("timestamp", "0"))
        if request.path.endswith("/rt") and day_ms > datetime.now().timestamp() * 1000:
            return EcosMockServer._ok_response(
                code=20404, message="Parameter verification failed", success=False
            )
        start = int(day_ms / 1000) // 900 * 900
        points = {str(start + 900 * i): float(100 * i) for i in range(4)}
        key = "pvForecastDps" if "/pv/" in request.path else "loadForecastDps"
        other = "loadForecastDps" if key == "pvForecastDps" else "pvForecastDps"
        return EcosMockServer._success_response(data={key: points, other: {}})

    async def handle_get_cost_info(self, request: web.Request) -> web.Response:
        """Mock home cost info endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data={
                "todaySavings": 0.99,
                "weeklySavings": [
                    {
                        "day": 1700000000000,
                        "loadCost": 4.1,
                        "gridCost": 3.5,
                        "feedEarnings": 0.0,
                        "daySavings": 0.6,
                    }
                ],
                "monthSavings": 53.6,
                "monthLoadCost": 121.4,
                "monthGridCost": 68.0,
                "monthFeedEarnings": 0.2,
            }
        )

    async def handle_get_week_energy(self, request: web.Request) -> web.Response:
        """Mock home week energy endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        if str(request.query.get("homeId")) != "9876543210987654321":
            return EcosMockServer._ok_response(
                code=20450, message="Home does not exist.", success=False
            )
        return EcosMockServer._success_response(
            data={
                "today": 1,
                "lastWeekTotalSolar": 28.0,
                "lastWeekTotalGrid": 56.4,
                "lastWeekTotalCarbonEmissions": 27.9,
                "lastWeekTotalSaveStandardCoal": 11.3,
                "weekEnergy": {
                    "2": {
                        "solarEnergy": 2.0,
                        "gridEnergy": 10.8,
                        "toGrid": 0.0,
                        "homeEnergy": 12.8,
                        "selfPowered": 16.0,
                    },
                    "1": {
                        "solarEnergy": 6.4,
                        "gridEnergy": 4.8,
                        "toGrid": 1.2,
                        "homeEnergy": 7.8,
                        "selfPowered": 67.0,
                    },
                },
                "carbonEmissionsWeekEnergy": {
                    "1": {"carbonEmissions": 6.4},
                    "2": {"carbonEmissions": 2.0},
                },
                "saveStandardCoalWeekEnergy": {
                    "1": {"saveStandardCoal": 2.6},
                    "2": {"saveStandardCoal": 0.8},
                },
            }
        )

    async def handle_get_backup_statistics(self, request: web.Request) -> web.Response:
        """Mock backup statistics endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data={"backupCount": 2, "backupEnergy": 1.5, "backupDuration": 3.25}
        )

    async def handle_get_unread_message_count(
        self, request: web.Request
    ) -> web.Response:
        """Mock unread message count endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        return EcosMockServer._success_response(
            data={"deviceMessageCount": 1, "officialMessageCount": 0}
        )

    async def handle_get_fixed_price(self, request: web.Request) -> web.Response:
        """Mock fixed electricity price endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        if str(request.query.get("homeId")) != "9876543210987654321":
            return EcosMockServer._success_response(data=None)
        return EcosMockServer._success_response(
            data={
                "id": 1,
                "homeId": 9876543210987654321,
                "purchasePrice": 0.32,
                "purchaseTax": 0.0,
                "feedInPrice": 0.08,
            }
        )

    async def handle_get_history(self, request: web.Request) -> web.Response:
        """Mock get history endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        request_payload = await request.json()
        logger.debug(request_payload)
        if str(request_payload.get("deviceId")) != "1234567890123456789":
            return EcosMockServer._response(
                code=20424,
                message="unauthorized device",
                success=False,
                http_status=401,
            )
        if request_payload.get("periodType") not in (0, 1, 2, 3, 4):
            return EcosMockServer._ok_response(
                code=20404, message="Parameter verification failed", success=False
            )
        # TODO other period time
        if request_payload.get("periodType") != 4:
            return EcosMockServer._not_implemented_response()
        current_month_timestamp = int(
            datetime.today()
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )
        return EcosMockServer._success_response(
            data={
                "energyConsumption": 924.7,
                "solarPercent": 54.0,
                "homeEnergyDps": {current_month_timestamp: 924.7},
            }
        )

    async def handle_get_insight(self, request: web.Request) -> web.Response:
        """Mock the get insight endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        request_payload = await request.json()
        logger.debug(request_payload)
        if str(request_payload.get("deviceId")) != "1234567890123456789":
            return EcosMockServer._response(
                code=20424,
                message="unauthorized device",
                success=False,
                http_status=401,
            )
        if request_payload.get("periodType") not in (0, 2, 4, 5):
            return EcosMockServer._ok_response(
                code=20404, message="Parameter verification failed", success=False
            )
        if (
            request_payload.get("periodType") == 0
        ):  # 5-minute power measurement for the provided day
            start_date = datetime.fromtimestamp(
                int(
                    request_payload.get(
                        "timestamp", int(datetime.now().timestamp() * 1000)
                    )
                    / 1000
                )
            ).replace(
                hour=0, minute=0, second=0, microsecond=0
            )  # convert timestamp (in milliseconds) to datetime
            end_date = start_date + timedelta(days=1)
            fake_data: dict[str, float] = await self._generate_metrics_data(
                start_date, end_date
            )
            latest_timestamp = max(fake_data.keys())
            fake_data[str(int(latest_timestamp) - 1)] = fake_data.pop(
                latest_timestamp
            )  # rename the latest timestamp by (timestamp - 1 sec)
            return EcosMockServer._success_response(
                data={
                    "selfPowered": 31.0,
                    "deviceRealtimeDto": {
                        "solarPowerDps": fake_data,
                        "batteryPowerDps": fake_data,
                        "gridPowerDps": fake_data,
                        "meterPowerDps": fake_data,
                        "homePowerDps": fake_data,
                        "epsPowerDps": fake_data,
                    },
                    "deviceStatisticsDto": {
                        "consumptionEnergy": 42.5,
                        "fromBattery": 0.0,
                        "toBattery": 0.0,
                        "fromGrid": 29.2,
                        "toGrid": 6.3,
                        "fromSolar": 19.6,
                        "eps": 0.0,
                    },
                    "insightConsumptionDataDto": None,
                }
            )
        if (
            request_payload.get("periodType") == 2
        ):  # daily energy for the provided month
            start_date = datetime.fromtimestamp(
                int(
                    request_payload.get(
                        "timestamp", int(datetime.now().timestamp() * 1000)
                    )
                    / 1000
                )
            ).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )  # convert timestamp (in milliseconds) to datetime
            end_date = start_date + relativedelta(months=1)
            fake_data = await self._generate_metrics_data(
                start_date, end_date, interval=timedelta(days=1)
            )
            latest_timestamp = max(fake_data.keys())
            fake_data[str(int(latest_timestamp) - 1)] = fake_data.pop(
                latest_timestamp
            )  # rename the latest timestamp by (timestamp - 1 sec)
            return EcosMockServer._success_response(
                data={
                    "selfPowered": 31.0,
                    "deviceRealtimeDto": None,
                    "deviceStatisticsDto": {
                        "consumptionEnergy": 42.5,
                        "fromBattery": 0.0,
                        "toBattery": 0.0,
                        "fromGrid": 29.2,
                        "toGrid": 6.3,
                        "fromSolar": 19.6,
                        "eps": 0.0,
                    },
                    "insightConsumptionDataDto": {
                        "fromBatteryDps": fake_data,
                        "toBatteryDps": fake_data,
                        "fromGridDps": fake_data,
                        "toGridDps": fake_data,
                        "fromSolarDps": fake_data,
                        "homeEnergyDps": fake_data,
                        "epsDps": fake_data,
                        "selfPoweredDps": fake_data,
                    },
                }
            )
        # if request_payload.get("periodType") not in (0, 2):
        return EcosMockServer._not_implemented_response()

    async def handle_get_fault_events(self, request: web.Request) -> web.Response:
        """Mock the get fault events endpoint."""
        if not self._is_authorized_request(request):
            return EcosMockServer._unauthorized_response()
        request_payload = await request.json()
        logger.debug(request_payload)
        if str(request_payload.get("deviceId")) != "1234567890123456789":
            return EcosMockServer._response(
                code=20424,
                message="unauthorized device",
                success=False,
                http_status=401,
            )
        if "type" not in request_payload:
            # The live API (EU, 2026-11-23) fails without it
            return EcosMockServer._response(
                code=500,
                message="Parameter specified as non-null is null: parameter eventType",
                success=False,
                http_status=500,
            )
        if not request_payload.get("start") or not request_payload.get("end"):
            return EcosMockServer._response(
                code=20000,
                message="cannot be null",
                success=False,
                http_status=200,
            )
        page_size = request_payload.get("pageSize", 10)
        page_num = max(request_payload.get("pageNum", 1), 1)

        # Event catalog
        event_catalog = [
            {
                "errorCode": "event_0",
                "eventType": "event",
                "eventTypeInt": 0,
                "eventContentEn": "Waiting for Grid",
                "eventContentCn": "等待电网模式",
                "eventAction": None,
            },
            {
                "errorCode": "dsp_10",
                "eventType": "fault",
                "eventTypeInt": 2,
                "eventContentEn": "Grid Off Fault",
                "eventContentCn": "无市电",
                "eventAction": None,
            },
            {
                "errorCode": "dsp_11",
                "eventType": "fault",
                "eventTypeInt": 2,
                "eventContentEn": "Grid Voltage Undertrip/Overtrip Fault",
                "eventContentCn": "电网电压故障",
                "eventAction": None,
            },
            {
                "errorCode": "event_5",
                "eventType": "event",
                "eventTypeInt": 0,
                "eventContentEn": "Checking",
                "eventContentCn": "进入自检模式",
                "eventAction": None,
            },
            {
                "errorCode": "event_1",
                "eventType": "event",
                "eventTypeInt": 0,
                "eventContentEn": "Grid Connected",
                "eventContentCn": "进入并网模式",
                "eventAction": None,
            },
        ]
        # Generate some fake events within the date range
        start_date = datetime.fromtimestamp(request_payload.get("start"))
        end_date = datetime.fromtimestamp(request_payload.get("end"))
        delta = end_date - start_date
        fake_events: list[JSON] = []
        current_date = start_date
        # "" returns every type, otherwise only the requested one (fault, alarm, event)
        wanted = request_payload["type"]
        catalog = [e for e in event_catalog if not wanted or e["eventType"] == wanted]
        while catalog and current_date < end_date:
            random_event = dict(random.choice(catalog))
            random_event["occurrenceTime"] = current_date.strftime("%Y-%m-%d %H:%M:%S")
            fake_events.append(random_event)
            current_date += delta / 20  # create 20 events evenly spaced
        # slicing for pagination
        start_index = (page_num - 1) * page_size
        end_index = start_index + page_size
        return EcosMockServer._success_response(
            data={
                "totalCount": len(fake_events),
                "totalPages": (len(fake_events) + page_size - 1) // page_size,
                "data": fake_events[start_index:end_index],
            }
        )

    async def handle_slow(self, request: web.Request) -> web.Response:
        """Endpoint that delays before responding (used to test request timeouts)."""
        await asyncio.sleep(1.0)
        return self._success_response({"slept": True})

    async def handle_drip(self, request: web.Request) -> web.StreamResponse:
        """Send a success response in 10 pieces over `seconds` (tests the total timeout)."""
        body = self._success_response({"dripped": True}).body
        assert isinstance(body, bytes)
        interval = float(request.query["seconds"]) / 10
        step = -(-len(body) // 10)  # ceiling division: 10 pieces at most
        response = web.StreamResponse(headers={"Content-Type": "application/json"})
        response.content_length = len(body)
        await response.prepare(request)
        for start in range(0, len(body), step):
            await asyncio.sleep(interval)
            await response.write(body[start : start + step])
        return response

    async def handle_malformed(self, request: web.Request) -> web.Response:
        """Return HTTP 200 with valid JSON that lacks the expected envelope keys."""
        return web.json_response({"foo": "bar"}, status=200)

    async def handle_non_object(self, request: web.Request) -> web.Response:
        """Return HTTP 200 with valid JSON that is not an object."""
        return web.json_response(["not", "an", "object"], status=200)

    async def handle_invalid_json(self, request: web.Request) -> web.Response:
        """Return HTTP 200 with a JSON content type and a body that is not JSON."""
        return web.Response(
            text="{not json", content_type="application/json", status=200
        )

    async def handle_deep_json(self, request: web.Request) -> web.Response:
        """Return HTTP 200 with JSON nested deeper than the parser's recursion limit."""
        return web.Response(
            text="[" * 100_000 + "]" * 100_000,
            content_type="application/json",
            status=200,
        )

    async def handle_hostile(self, request: web.Request) -> web.Response:
        """Return HTTP 200 with a successful response whose `data` is malformed.

        Serves any API path under `/hostile/<scenario>/`; the `missing` scenario
        has no `data` at all.
        """
        timestamp = "1740783600"
        event = {"occurrenceTime": "2025-03-01 00:00:00"}
        scenarios: dict[str, JSON] = {
            "null": None,
            "string": "data",
            "list": [42],
            "tokens-not-strings": {"accessToken": 42, "refreshToken": None},
            "series-null": {
                "energyConsumption": 1.0,
                "solarPercent": 1.0,
                "homePowerDps": None,
                "homeEnergyDps": None,
            },
            "series-list": {
                "energyConsumption": 1.0,
                "solarPercent": 1.0,
                "homePowerDps": [42],
                "homeEnergyDps": [42],
            },
            "series-string": {
                "energyConsumption": 1.0,
                "solarPercent": 1.0,
                "homePowerDps": "data",
                "homeEnergyDps": "data",
            },
            "timestamp-not-a-number": {
                "energyConsumption": 1.0,
                "solarPercent": 1.0,
                "homePowerDps": {"now": 1.0},
                "homeEnergyDps": {"now": 1.0},
            },
            "other-series-null": {
                "homePowerDps": {timestamp: 1.0},
                "solarPowerDps": None,
            },
            "other-series-bool": {
                "homePowerDps": {timestamp: 1.0},
                "solarPowerDps": True,
            },
            "metrics-not-a-list": {"metrics": 42},
            "insight-series-list": {
                "selfPowered": 1,
                "deviceRealtimeDto": [],
                "deviceStatisticsDto": None,
                "insightConsumptionDataDto": None,
            },
            "insight-consumption-list": {
                "selfPowered": 1,
                "deviceRealtimeDto": None,
                "deviceStatisticsDto": None,
                "insightConsumptionDataDto": [],
            },
            "insight-other-series-null": {
                "selfPowered": 1,
                "deviceRealtimeDto": None,
                "deviceStatisticsDto": None,
                "insightConsumptionDataDto": {
                    "homeEnergyDps": {timestamp: 1.0},
                    "epsDps": None,
                },
            },
            "insight-other-series-number": {
                "selfPowered": 1,
                "deviceRealtimeDto": None,
                "deviceStatisticsDto": None,
                "insightConsumptionDataDto": {
                    "homeEnergyDps": {timestamp: 1.0},
                    "epsDps": 42,
                },
            },
            "insight-metrics-not-a-list": {
                "selfPowered": 1,
                "deviceRealtimeDto": None,
                "deviceStatisticsDto": None,
                "insightConsumptionDataDto": {"metrics": 42},
            },
            "events-null": {"data": None},
            "event-code-list": {"data": [{**event, "errorCode": ["event_0"]}]},
            "event-type-number": {
                "data": [{**event, "errorCode": "unknown_0", "eventType": 2}]
            },
            "week-series-list": {"weekEnergy": [42]},
            "week-values-list": {"weekEnergy": {"1": [42]}},
            "forecast-series-list": {"pvForecastDps": [42]},
            "first-install-infinity": {"firstInstall": float("inf")},
        }
        scenario = request.match_info["scenario"]
        output: JSON = {"code": 0, "message": "success", "success": True}
        if scenario != "missing":
            output["data"] = scenarios[scenario]
        return web.json_response(output, status=200)

    async def handle_charset(self, request: web.Request) -> web.Response:
        """Return HTTP 200 with a JSON content type naming the requested charset."""
        charset = request.match_info["charset"]
        return web.Response(
            body=b'{"code": 0, "message": "success", "success": true, "data": {}}',
            headers={"Content-Type": f"application/json; charset={charset}"},
            status=200,
        )

    async def catch_all(self, request: web.Request) -> web.Response:
        """Catch all endpoint."""
        # if request.path starts with /api/client/ then
        if request.path.startswith("/api/client/"):
            path_after = request.path[11:]  # get the path after /api/client
            ts = int(
                datetime.now().timestamp() * 1000
            )  # get the current timestamp in milliseconds
            return web.json_response(
                {
                    "timestamp": ts,
                    "status": 404,
                    "error": "Not Found",
                    "message": "",
                    "path": path_after,
                },
                status=404,
            )
        if request.path == "/api/client":
            return web.HTTPMovedPermanently("/api/client/")  # redirect to /api/client/
        # else
        return web.HTTPBadGateway()

    def setup_routes(self) -> None:
        """Configure routes."""
        logger.info("Setting up routes")
        self.app.add_routes(
            [
                web.post("/api/client/guide/login", self.handle_login),
                web.get("/api/client/settings/user/info", self.handle_get_user_info),
                web.get("/api/client/v2/home/family/query", self.handle_get_homes),
                web.get("/api/client/v2/home/device/query", self.handle_get_devices),
                web.get("/api/client/home/device/list", self.handle_get_all_devices),
                web.post(
                    "/api/client/home/now/device/realtime",
                    self.handle_get_today_device_data,
                ),
                web.get(
                    "/api/client/v2/home/device/runData",
                    self.handle_get_realtime_home_data,
                ),
                web.post(
                    "/api/client/home/now/device/runData",
                    self.handle_get_realtime_device_data,
                ),
                web.post("/api/client/home/history/home", self.handle_get_history),
                web.post(
                    "/api/client/v2/device/three/device/insight",
                    self.handle_get_insight,
                ),
                web.post(
                    "/api/client/home/events/fault",
                    self.handle_get_fault_events,
                ),
                web.get(
                    "/api/client/v2/device/three/device/detail",
                    self.handle_get_device_detail,
                ),
                web.get("/api/client/customize/info", self.handle_get_device_settings),
                web.get(
                    "/api/client/v2/home/device/mode", self.handle_get_device_modes
                ),
                web.get(
                    "/api/client/v2/device/three/device/power_limit",
                    self.handle_get_power_limit,
                ),
                web.get(
                    "/api/client/v2/home/device/insight/{kind:pv|load}/forecast",
                    self.handle_get_forecast,
                ),
                web.get(
                    "/api/client/v2/home/device/insight/{kind:pv|load}/forecast/rt",
                    self.handle_get_forecast,
                ),
                web.get("/api/client/v2/home/cost/info", self.handle_get_cost_info),
                web.get(
                    "/api/client/v2/home/device/energy", self.handle_get_week_energy
                ),
                web.post(
                    "/api/client/home/events/backup/statistics",
                    self.handle_get_backup_statistics,
                ),
                web.post(
                    "/api/client/message/count_unread",
                    self.handle_get_unread_message_count,
                ),
                web.get("/api/client/ele/price/fixed/get", self.handle_get_fixed_price),
                web.get("/slow", self.handle_slow),
                web.get("/drip", self.handle_drip),
                web.get("/malformed", self.handle_malformed),
                web.get("/non-object", self.handle_non_object),
                web.post("/non-object", self.handle_non_object),
                web.get("/invalid-json", self.handle_invalid_json),
                web.get("/deep-json", self.handle_deep_json),
                web.route("*", "/hostile/{scenario}/{path:.*}", self.handle_hostile),
                web.get("/charset/{charset}", self.handle_charset),
                web.route("*", "/+{path:.*}", self.catch_all),
            ]
        )

    def run(self) -> None:
        """Run the server."""
        logger.info("Running server")
        self.setup_routes()
        self.url = f"http://{self.host}:{self.port}"
        web.run_app(self.app, host=self.host, port=self.port)

    async def start(self) -> None:
        """Start the server asynchronously."""
        logger.info("Starting server")
        self.setup_routes()
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host=self.host, port=self.port)
        self.url = f"http://{self.host}:{self.port}"
        await site.start()

    async def stop(self) -> None:
        """Stop the server."""
        logger.info("Stopping server")
        if self._runner is not None:
            await self._runner.cleanup()


"""
if __name__ == "__main__":
    server = EcosMockServer()
    server.run()
"""


async def main() -> None:
    """Run the server."""
    server = EcosMockServer()
    await server.start()
    print(f"Running server on {server.url}")  # noqa: T201
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("Process interrupted")  # noqa: T201
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
