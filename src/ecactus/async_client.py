"""Implementation of an asynchronous class for interacting with the ECOS API."""

from datetime import datetime
import logging
import math
import time
from typing import Any, Literal

from pydantic import ConfigDict, TypeAdapter

from .base import _BaseEcos
from .exceptions import (
    ApiResponseError,
    AuthenticationError,
    HomeDoesNotExistError,
    InvalidJsonError,
    ParameterVerificationFailedError,
    UnauthorizedDeviceError,
    UnauthorizedError,  # noqa: F401 # imported to make it available in the docs
)
from .model import (
    BackupStatistics,
    CostInfo,
    Device,
    DeviceDetail,
    DeviceInsight,
    DeviceMode,
    DeviceSettings,
    EnergyHistory,
    Event,
    FixedPrice,
    Forecast,
    Home,
    MessageCount,
    PowerMetrics,
    PowerTimeSeries,
    User,
    WeatherDay,
    WeatherHour,
    WeatherNow,
    WeekEnergy,
)

# Configure logging
logger = logging.getLogger(__name__)

# Anything but a list of objects in the `data` of a list endpoint, or a number
# for the power limit, raises a ValidationError, as a malformed object does. An
# adapter is the root of its validation, so it carries the setting that keeps
# the input out of the error message, as the models do.
_ADAPTER_CONFIG = ConfigDict(hide_input_in_errors=True)
_HOME_LIST = TypeAdapter(list[Home], config=_ADAPTER_CONFIG)
_DEVICE_LIST = TypeAdapter(list[Device], config=_ADAPTER_CONFIG)
_EVENT_LIST = TypeAdapter(list[Event], config=_ADAPTER_CONFIG)
_DEVICE_MODE_LIST = TypeAdapter(list[DeviceMode], config=_ADAPTER_CONFIG)
_POWER_LIMIT = TypeAdapter(float | None, config=_ADAPTER_CONFIG)
_WEATHER_HOURS = TypeAdapter(list[WeatherHour], config=_ADAPTER_CONFIG)
_WEATHER_DAYS = TypeAdapter(list[WeatherDay], config=_ADAPTER_CONFIG)


class AsyncEcos(_BaseEcos):
    """Asynchronous ECOS API client class.

    This class provides methods for interacting with the ECOS API, including
    authentication, retrieving user information, and managing homes. It uses
    the `aiohttp` library to make asynchronous HTTP requests to the API.
    """

    async def login(
        self, email: str | None = None, password: str | None = None
    ) -> None:
        """Authenticate with the ECOS API using a provided email and password.

        Args:
            email: The user's email to use for authentication.
            password: The user's password to use for authentication.

        Raises:
            AuthenticationError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            InvalidJsonError: If the response carries no access and refresh tokens.

        """
        logger.info("Login")
        if email is not None:
            self.email = email
        if password is not None:
            self.password = password
        payload: dict[str, Any] = {
            "_t": int(time.time()),
            "clientType": "BROWSER",
            "clientVersion": "1.0",
            "email": self.email,
            "password": self.password,
        }
        try:
            data = await self._async_post("/api/client/guide/login", payload=payload)
        except ApiResponseError as err:
            if err.code == 20414:
                raise AuthenticationError from err
            if err.code == 20000:
                raise AuthenticationError("Missing Account or Password") from err
            raise
        if not (
            isinstance(data, dict)
            and isinstance(data.get("accessToken"), str)
            and isinstance(data.get("refreshToken"), str)
        ):
            raise InvalidJsonError(
                "Login response carries no access and refresh tokens"
            )
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]

    async def _ensure_login(self) -> None:
        """Ensure that the user is logged in by checking the validity of the access token."""
        if self.access_token is None:
            await self.login()

    async def get_user(self) -> User:
        """Get user details.

        Returns:
            A User object.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get user")
        await self._ensure_login()
        return User.model_validate(
            await self._async_get("/api/client/settings/user/info")
        )

    async def get_homes(self) -> list[Home]:
        """Get a list of homes.

        Returns:
            A list of Home objects.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get home list")
        await self._ensure_login()
        return _HOME_LIST.validate_python(
            await self._async_get("/api/client/v2/home/family/query")
        )

    async def get_devices(self, home_id: str) -> list[Device]:
        """Get a list of devices for a home.

        Args:
            home_id: The home ID to get devices for.

        Returns:
            A list of Device objects.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get devices for home %s", home_id)
        await self._ensure_login()
        try:
            return _DEVICE_LIST.validate_python(
                await self._async_get(
                    "/api/client/v2/home/device/query", payload={"homeId": home_id}
                )
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err
            raise

    async def get_all_devices(self) -> list[Device]:
        """Get a list of all the devices.

        Returns:
            A list of Device objects.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get devices for every homes")
        await self._ensure_login()
        return _DEVICE_LIST.validate_python(
            await self._async_get("/api/client/home/device/list")
        )

    async def get_today_device_data(self, device_id: str) -> PowerTimeSeries:
        """Get power metrics of the current day until now.

        Args:
            device_id: The device ID to get power metrics for.

        Returns:
            Metrics of the current day until now.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get current day data for device %s", device_id)
        await self._ensure_login()
        try:
            return PowerTimeSeries.model_validate(
                await self._async_post(
                    "/api/client/home/now/device/realtime",
                    payload={"deviceId": device_id},
                )
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            raise

    async def get_realtime_home_data(self, home_id: str) -> PowerMetrics:
        """Get current power for the home.

        Args:
            home_id: The home ID to get current power for.

        Returns:
            Current metrics for the home.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get realtime data for home %s", home_id)
        await self._ensure_login()
        try:
            return PowerMetrics.model_validate(
                await self._async_get(
                    "/api/client/v2/home/device/runData", payload={"homeId": home_id}
                )
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err
            raise

    async def get_realtime_device_data(self, device_id: str) -> PowerMetrics:
        """Get current power for a device.

        Args:
            device_id: The device ID to get current power for.

        Returns:
            Current metrics for the device.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get realtime data for device %s", device_id)
        await self._ensure_login()
        try:
            return PowerMetrics.model_validate(
                await self._async_post(
                    "/api/client/home/now/device/runData",
                    payload={"deviceId": device_id},
                )
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            raise

    async def get_history(
        self, device_id: str, period_type: int, start_date: datetime | None = None
    ) -> EnergyHistory:
        """Get aggregated energy for a period.

        Args:
            device_id: The device ID to get history for.
            period_type: Possible value (observed on one device, EU datacenter):

                - `0`: daily values of the calendar month containing `start_date`
                - `1`: daily values of the last three days, today included (`start_date` is ignored)
                - `2`: daily values of the current month (`start_date` is ignored)
                - `3`: daily values of the previous and the current month (`start_date` is ignored)
                - `4`: monthly values up to the current month, `energy_consumption` being their total (`start_date` is ignored); on a device installed in the current year this covers every month since installation, whether earlier years are included is not known
            start_date: The start date, required for `period_type` 0.

        Returns:
            Data and metrics corresponding to the defined period.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            ParameterVerificationFailedError: If a parameter is not valid (`period_type` number for example)
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get history for device %s", device_id)
        await self._ensure_login()
        if start_date is None:
            if period_type in (1, 2, 3, 4):
                start_ts = 0
            else:
                raise ParameterVerificationFailedError(
                    f"start_date is required for period_type {period_type}"
                )
        else:
            start_ts = int(start_date.timestamp())
        try:
            return EnergyHistory.model_validate(
                await self._async_post(
                    "/api/client/home/history/home",
                    payload={
                        "deviceId": device_id,
                        "timestamp": start_ts,
                        "periodType": period_type,
                    },
                )
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            if err.code == 20404:
                raise ParameterVerificationFailedError from err
            raise

    async def get_insight(
        self, device_id: str, period_type: int, start_date: datetime | None = None
    ) -> DeviceInsight:
        """Get energy metrics and statistics of a device for a period.

        Args:
            device_id: The device ID to get data for.
            period_type: Possible value:

                - `0`: 15-minute power measurements (96 per day) for the calendar day containing `start_date` (`insightConsumptionDataDto` is `None`)
                - `1`: rejected by the API (`ParameterVerificationFailedError`)
                - `2`: daily energy for the calendar month containing `start_date` (`deviceRealtimeDto` is `None`)
                - `3`: rejected by the API (`ParameterVerificationFailedError`)
                - `4`: monthly energy for the calendar year containing `start_date` (`deviceRealtimeDto` is `None`)
                - `5`: yearly energy, one entry per calendar year; `start_date` is ignored (`deviceRealtimeDto` is `None`). On a device installed in the current year, its statistics match the lifetime counters of the installer app.

                The calendar day, month or year is taken in local time (observed on
                one device in Europe/Berlin, EU datacenter).
            start_date: The start date.

        Returns:
            Statistics and metrics corresponding to the defined period.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            ParameterVerificationFailedError: If a parameter is not valid (`period_type` number for example)
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get insight for device %s", device_id)
        await self._ensure_login()
        if start_date is None:
            if period_type == 5:
                start_ts = 0
            else:
                raise ParameterVerificationFailedError(
                    f"start_date is required for period_type {period_type}"
                )
        else:
            start_ts = int(start_date.timestamp() * 1000)  # timestamp in milliseconds
        try:
            return DeviceInsight.model_validate(
                await self._async_post(
                    "/api/client/v2/device/three/device/insight",
                    payload={
                        "deviceId": device_id,
                        "timestamp": start_ts,
                        "periodType": period_type,
                    },
                )
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            if err.code == 20404:
                raise ParameterVerificationFailedError from err
            raise

    async def get_fault_events(
        self,
        device_id: str,
        start_date: datetime,
        end_date: datetime,
        *,
        event_type: Literal["fault", "alarm", "event"] | None = None,
    ) -> list[Event]:
        """Get the events of a device: faults, alarms and state changes.

        All three types are returned unless `event_type` filters them.

        Args:
            device_id: The device ID to get events for.
            start_date: The start date.
            end_date: The end date.
            event_type: Only return this type: `"fault"`, `"alarm"` or `"event"`
                (state changes such as "Grid Connected"). None returns all of them.

        Returns:
            A list of events.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            InvalidJsonError: If the response is not an object.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get events for device %s", device_id)
        await self._ensure_login()
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        try:
            output = await self._async_post(
                "/api/client/home/events/fault",
                payload={
                    "deviceId": device_id,
                    "start": start_ts,
                    "end": end_ts,
                    "pageSize": 1000000,  # large number to get all events in one call
                    "pageNum": 0,
                    # Required: without it, or with null, the API answers HTTP 500
                    # "parameter eventType is null" (EU, 2026-11-23). "" selects all types.
                    "type": event_type or "",
                },
            )
        except ApiResponseError as err:
            # The live API answers 20412 "illegal data operation" for an unknown device
            # on this endpoint (EU, 2026-11-24), other endpoints answer 20424
            if err.code in (20412, 20424):
                raise UnauthorizedDeviceError(device_id) from err
            raise
        if not isinstance(output, dict):
            raise InvalidJsonError("Fault events response is not an object")
        return _EVENT_LIST.validate_python(output.get("data", []))

    async def get_device_detail(self, device_id: str) -> DeviceDetail:
        """Get the details of a three-phase device (model, rated power, battery capacity, firmware).

        Only verified with a three-phase inverter (Agave TH). The ECOS web client
        uses `/v2/device/single/device/detail` for single-phase devices instead.

        Args:
            device_id: The device ID.

        Returns:
            The device details.

        Raises:
            UnauthorizedDeviceError: If the device id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get detail for device %s", device_id)
        await self._ensure_login()
        try:
            return DeviceDetail.model_validate(
                await self._async_get(
                    "/api/client/v2/device/three/device/detail",
                    payload={"deviceId": device_id},
                )
            )
        except ApiResponseError as err:
            # The live API answers 20450 "The device does not exist." for an unknown
            # device on this endpoint (EU, 2026-11-23), the code of an unknown home
            if err.code == 20450:
                raise UnauthorizedDeviceError(device_id) from err
            raise

    async def get_device_settings(self, device_id: str) -> DeviceSettings:
        """Get the operating settings of a device (battery reserves, feed-in, charge windows, firmware).

        Args:
            device_id: The device ID.

        Returns:
            The device settings.

        Raises:
            UnauthorizedDeviceError: If the device id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get settings for device %s", device_id)
        await self._ensure_login()
        try:
            return DeviceSettings.model_validate(
                await self._async_get(
                    "/api/client/customize/info", payload={"deviceId": device_id}
                )
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            raise

    async def get_device_modes(self, home_id: str) -> list[DeviceMode]:
        """Get the operating mode of every device of a home.

        Args:
            home_id: The home ID.

        Returns:
            One DeviceMode per device.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get device modes for home %s", home_id)
        await self._ensure_login()
        try:
            return _DEVICE_MODE_LIST.validate_python(
                await self._async_get(
                    "/api/client/v2/home/device/mode", payload={"homeId": home_id}
                )
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err
            raise

    async def get_power_limit(self, device_id: str) -> float:
        """Get the main grid connection limit of a three-phase device.

        Shown as "main power connection limit" in the installer app.

        Args:
            device_id: The device ID.

        Returns:
            The power limit as returned by the API (0 when no limit is set).

        Raises:
            UnauthorizedDeviceError: If the device id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get power limit for device %s", device_id)
        await self._ensure_login()
        try:
            value = await self._async_get(
                "/api/client/v2/device/three/device/power_limit",
                payload={"deviceId": device_id},
            )
        except ApiResponseError as err:
            # The live API answers 20412 "illegal data operation" for an unknown device
            # on this endpoint (EU, 2026-11-23), like get_fault_events
            if err.code == 20412:
                raise UnauthorizedDeviceError(device_id) from err
            raise
        return _POWER_LIMIT.validate_python(value) or 0.0

    async def _get_forecast(
        self, kind: str, home_id: str, day: datetime, realtime: bool
    ) -> Forecast:
        """Get a PV or load forecast (shared implementation)."""
        logger.info("Get %s forecast for home %s", kind, home_id)
        await self._ensure_login()
        path = f"/api/client/v2/home/device/insight/{kind}/forecast"
        if realtime:
            path += "/rt"
        try:
            return Forecast.model_validate(
                await self._async_get(
                    path,
                    payload={
                        "homeId": home_id,
                        "timestamp": str(int(day.timestamp() * 1000)),
                    },
                )
            )
        except ApiResponseError as err:
            if err.code == 20404:
                raise ParameterVerificationFailedError from err
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err
            raise

    async def get_pv_forecast(
        self, home_id: str, day: datetime, realtime: bool = False
    ) -> Forecast:
        """Get the PV production forecast of a home for one calendar day, in 15-minute points.

        Args:
            home_id: The home ID.
            day: Any time of the requested day. Yesterday, today and tomorrow are
                available; later days return an empty forecast.
            realtime: Use the forecast that the cloud updates during the day
                (`/rt`). Only available up to today.

        Returns:
            The forecast in watts.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            ParameterVerificationFailedError: If the day is not available (e.g. a future day with `realtime`).
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        return await self._get_forecast("pv", home_id, day, realtime)

    async def get_load_forecast(
        self, home_id: str, day: datetime, realtime: bool = False
    ) -> Forecast:
        """Get the home consumption forecast of a home for one calendar day, in 15-minute points.

        Args:
            home_id: The home ID.
            day: Any time of the requested day. Yesterday, today and tomorrow are
                available.
            realtime: Use the forecast that the cloud updates during the day
                (`/rt`). Only available up to today.

        Returns:
            The forecast in watts.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            ParameterVerificationFailedError: If the day is not available.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        return await self._get_forecast("load", home_id, day, realtime)

    async def get_cost_info(self, home_id: str) -> CostInfo:
        """Get the costs and savings of a home as computed by the ECOS cloud.

        The API does not report an unknown home: it answers with every value
        `None` (EU, 2026-11-23), as for a home without cost data.

        Args:
            home_id: The home ID.

        Returns:
            Savings of today, of the last days and of the current month.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get cost info for home %s", home_id)
        await self._ensure_login()
        return CostInfo.model_validate(
            await self._async_get(
                "/api/client/v2/home/cost/info", payload={"homeId": home_id}
            )
        )

    async def get_week_energy(self, home_id: str) -> WeekEnergy:
        """Get the energy of the last seven days as shown on the home screen of the ECOS app.

        Args:
            home_id: The home ID.

        Returns:
            Energy per weekday and totals of the last seven days.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get week energy for home %s", home_id)
        await self._ensure_login()
        try:
            return WeekEnergy.model_validate(
                await self._async_get(
                    "/api/client/v2/home/device/energy", payload={"homeId": home_id}
                )
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err
            raise

    async def get_backup_statistics(
        self, device_id: str, start_date: datetime, end_date: datetime
    ) -> BackupStatistics:
        """Get the backup (EPS) statistics of a device over a period.

        Args:
            device_id: The device ID.
            start_date: The start date.
            end_date: The end date.

        Returns:
            Number, energy and duration of the backup events.

        Raises:
            UnauthorizedDeviceError: If the device id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get backup statistics for device %s", device_id)
        await self._ensure_login()
        try:
            return BackupStatistics.model_validate(
                await self._async_post(
                    "/api/client/home/events/backup/statistics",
                    payload={
                        "deviceId": device_id,
                        "startTime": int(start_date.timestamp()),
                        "endTime": int(end_date.timestamp()),
                    },
                )
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            raise

    async def get_unread_message_count(self) -> MessageCount:
        """Get the number of unread messages of the account.

        Returns:
            Unread device and official messages.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get unread message count")
        await self._ensure_login()
        return MessageCount.model_validate(
            await self._async_post("/api/client/message/count_unread")
        )

    async def get_fixed_price(self, home_id: str) -> FixedPrice | None:
        """Get the fixed electricity price configured for a home.

        Args:
            home_id: The home ID.

        Returns:
            The configured prices, or None if no fixed price is set. The API
                answers the same for an unknown home (EU, 2026-11-23).

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get fixed price for home %s", home_id)
        await self._ensure_login()
        data = await self._async_get(
            "/api/client/ele/price/fixed/get", payload={"homeId": home_id}
        )
        return FixedPrice.model_validate(data) if data else None

    @staticmethod
    def _weather_location(longitude: float, latitude: float) -> dict[str, str]:
        """Build the `location` parameter of the weather endpoints.

        The weather service takes "longitude,latitude"; without it the API answers 403.
        Two decimals (about 1 km) are enough for weather and keep the request less
        precise than the home.

        Raises:
            ValueError: If a coordinate is not finite or out of range.

        """
        if not (math.isfinite(longitude) and -180 <= longitude <= 180):
            raise ValueError(f"longitude must be between -180 and 180, got {longitude}")
        if not (math.isfinite(latitude) and -90 <= latitude <= 90):
            raise ValueError(f"latitude must be between -90 and 90, got {latitude}")
        return {"location": f"{longitude:.2f},{latitude:.2f}"}

    async def get_weather_now(self, *, longitude: float, latitude: float) -> WeatherNow:
        """Get the current weather at a location, as shown in the ECOS app.

        Args:
            longitude: Longitude of the location in degrees (-180 to 180).
            latitude: Latitude of the location in degrees (-90 to 90).

        Both are rounded to two decimals (about 1 km) before they are sent. They are
        not written to the `ecactus` debug log, but they are part of the request URL,
        so they can appear in a `requests` connection error message and in the DEBUG
        log of `urllib3`.

        Returns:
            The current weather; every field is None if the weather service does not
                know the location.

        Raises:
            ValueError: If a coordinate is not finite or out of range.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get current weather")
        location = self._weather_location(longitude, latitude)
        await self._ensure_login()
        return WeatherNow.model_validate(
            await self._async_get("/api/client/home/weather/now", payload=location)
        )

    async def get_weather_hourly(
        self, *, longitude: float, latitude: float
    ) -> list[WeatherHour]:
        """Get the hourly weather forecast for the next 24 hours at a location.

        Args:
            longitude: Longitude of the location in degrees (-180 to 180).
            latitude: Latitude of the location in degrees (-90 to 90).

        Both are rounded to two decimals (about 1 km) before they are sent. They are
        not written to the `ecactus` debug log, but they are part of the request URL,
        so they can appear in a `requests` connection error message and in the DEBUG
        log of `urllib3`.

        Returns:
            One entry per hour, empty if the weather service does not know the location.

        Raises:
            ValueError: If a coordinate is not finite or out of range.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get hourly weather forecast")
        location = self._weather_location(longitude, latitude)
        await self._ensure_login()
        return _WEATHER_HOURS.validate_python(
            await self._async_get("/api/client/home/weather/24h", payload=location)
        )

    async def get_weather_daily(
        self, *, longitude: float, latitude: float
    ) -> list[WeatherDay]:
        """Get the daily weather forecast for the next 7 days at a location.

        Args:
            longitude: Longitude of the location in degrees (-180 to 180).
            latitude: Latitude of the location in degrees (-90 to 90).

        Both are rounded to two decimals (about 1 km) before they are sent. They are
        not written to the `ecactus` debug log, but they are part of the request URL,
        so they can appear in a `requests` connection error message and in the DEBUG
        log of `urllib3`.

        Returns:
            One entry per day, empty if the weather service does not know the location.

        Raises:
            ValueError: If a coordinate is not finite or out of range.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            pydantic.ValidationError: If the response data does not have the expected shape.

        """
        logger.info("Get daily weather forecast")
        location = self._weather_location(longitude, latitude)
        await self._ensure_login()
        return _WEATHER_DAYS.validate_python(
            await self._async_get("/api/client/home/weather/7d", payload=location)
        )
