"""Ecos API mock server."""

import asyncio
from datetime import datetime, timedelta
import logging
import random
import string
from typing import Any

from aiohttp import web
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
        data: dict = await request.json()  # Parse the JSON payload
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
        current_month_timestamp = (
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
        if request_payload.get("periodType") != 0:
            return EcosMockServer._not_implemented_response()
        start_date = datetime.fromtimestamp(
            int(request_payload.get("timestamp") / 1000)
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
