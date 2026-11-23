"""Implementation of a synchronous class for interacting with the ECOS API."""

from datetime import datetime
import logging
import time
from typing import Any

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


class Ecos(_BaseEcos):
    """Synchronous ECOS API client class.

    This class provides methods for interacting with the ECOS API, including
    authentication, retrieving user information, and managing homes. It uses
    the `requests` library to make HTTP requests to the API.
    """

    def login(
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
            data = self._post("/api/client/guide/login", payload=payload)
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

    def _ensure_login(self) -> None:
        """Ensure that the user is logged in by checking the validity of the access token."""
        if self.access_token is None:
            self.login()

    def get_user(self) -> User:
        """Get user details.

        Returns:
            A User object.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get user")
        self._ensure_login()
        return User.model_validate(
            self._get("/api/client/settings/user/info")
        )

    def get_homes(self) -> list[Home]:
        """Get a list of homes.

        Returns:
            A list of Home objects.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get home list")
        self._ensure_login()
        return _HOME_LIST.validate_python(
            self._get("/api/client/v2/home/family/query")
        )

    def get_devices(self, home_id: str) -> list[Device]:
        """Get a list of devices for a home.

        Args:
            home_id: The home ID to get devices for.

        Returns:
            A list of Device objects.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get devices for home %s", home_id)
        self._ensure_login()
        try:
            return _DEVICE_LIST.validate_python(
                self._get(
                    "/api/client/v2/home/device/query", payload={"homeId": home_id}
                )
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err
            raise

    def get_all_devices(self) -> list[Device]:
        """Get a list of all the devices.

        Returns:
            A list of Device objects.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get devices for every homes")
        self._ensure_login()
        return _DEVICE_LIST.validate_python(
            self._get("/api/client/home/device/list")
        )

    def get_today_device_data(self, device_id: str) -> PowerTimeSeries:
        """Get power metrics of the current day until now.

        Args:
            device_id: The device ID to get power metrics for.

        Returns:
            Metrics of the current day until now.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get current day data for device %s", device_id)
        self._ensure_login()
        try:
            return PowerTimeSeries.model_validate(
                self._post(
                    "/api/client/home/now/device/realtime",
                    payload={"deviceId": device_id},
                )
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            raise

    def get_realtime_home_data(self, home_id: str) -> PowerMetrics:
        """Get current power for the home.

        Args:
            home_id: The home ID to get current power for.

        Returns:
            Current metrics for the home.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get realtime data for home %s", home_id)
        self._ensure_login()
        try:
            return PowerMetrics.model_validate(
                self._get(
                    "/api/client/v2/home/device/runData", payload={"homeId": home_id}
                )
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err
            raise

    def get_realtime_device_data(self, device_id: str) -> PowerMetrics:
        """Get current power for a device.

        Args:
            device_id: The device ID to get current power for.

        Returns:
            Current metrics for the device.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get realtime data for device %s", device_id)
        self._ensure_login()
        try:
            return PowerMetrics.model_validate(
                self._post(
                    "/api/client/home/now/device/runData",
                    payload={"deviceId": device_id},
                )
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            raise

    def get_history(
        self, device_id: str, period_type: int, start_date: datetime | None = None
    ) -> EnergyHistory:
        """Get aggregated energy for a period.

        Args:
            device_id: The device ID to get history for.
            period_type: Possible value:

                - `0`: daily values of the calendar month corresponding to `start_date`
                - `1`: today daily values (`start_date` is ignored) (?)
                - `2`: daily values of the current month (`start_date` is ignored)
                - `3`: same than 2 ?
                - `4`: total for the current month (`start_date` is ignored)
            start_date: The start date.

        Returns:
            Data and metrics corresponding to the defined period.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            ParameterVerificationFailedError: If a parameter is not valid (`period_type` number for example)
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get history for device %s", device_id)
        self._ensure_login()
        if start_date is None:
            if period_type in (1, 2, 4):
                start_ts = 0
            else:
                raise ParameterVerificationFailedError(
                    f"start_date is required for period_type {period_type}"
                )
        else:
            start_ts = int(start_date.timestamp())
        try:
            return EnergyHistory.model_validate(
                self._post(
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

    def get_insight(
        self, device_id: str, period_type: int, start_date: datetime | None = None
    ) -> DeviceInsight:
        """Get energy metrics and statistics of a device for a period.

        Args:
            device_id: The device ID to get data for.
            period_type: Possible value:

                - `0`: 5-minute power measurement for the calendar day corresponding to `start_date` (`insightConsumptionDataDto` is `None`)
                - `1`: (not implemented)
                - `2`: daily energy for the calendar month corresponding to `start_date` (`deviceRealtimeDto` is `None`)
                - `3`: (not implemented)
                - `4`: monthly energy for the calendar year corresponding to `start_date` (`deviceRealtimeDto` is `None`)
                - `5`: yearly energy, `start_date` is ignored (?) (`deviceRealtimeDto` is `None`)
            start_date: The start date.

        Returns:
            Statistics and metrics corresponding to the defined period.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            ParameterVerificationFailedError: If a parameter is not valid (`period_type` number for example)
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get insight for device %s", device_id)
        self._ensure_login()
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
                self._post(
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

    def get_fault_events(
        self, device_id: str, start_date: datetime, end_date: datetime
    ) -> list[Event]:
        """Get fault events for a device.

        Args:
            device_id: The device ID to get events for.
            start_date: The start date.
            end_date: The end date.

        Returns:
            A list of events.

        Raises:
            UnauthorizedDeviceError: If the device is not authorized or unknown.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            InvalidJsonError: If the response is not an object.

        """
        logger.info("Get events for device %s", device_id)
        self._ensure_login()
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        try:
            output = self._post(
                "/api/client/home/events/fault",
                payload={
                    "deviceId": device_id,
                    "start": start_ts,
                    "end": end_ts,
                    "pageSize": 1000000,  # large number to get all events in one call
                    "pageNum": 0,
                },
            )
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            raise
        if not isinstance(output, dict):
            raise InvalidJsonError("Fault events response is not an object")
        return _EVENT_LIST.validate_python(output.get("data", []))

    def get_device_detail(self, device_id: str) -> DeviceDetail:
        """Get the details of a three-phase device (model, rated power, battery capacity, firmware).

        Only verified with a three-phase inverter (Agave TH). The ECOS web client
        uses `/v2/device/single/device/detail` for single-phase devices instead.

        Args:
            device_id: The device ID.

        Returns:
            The device details.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get detail for device %s", device_id)
        self._ensure_login()
        return DeviceDetail.model_validate(
            self._get(
                "/api/client/v2/device/three/device/detail",
                payload={"deviceId": device_id},
            )
        )

    def get_device_settings(self, device_id: str) -> DeviceSettings:
        """Get the operating settings of a device (battery reserves, feed-in, charge windows, firmware).

        Args:
            device_id: The device ID.

        Returns:
            The device settings.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get settings for device %s", device_id)
        self._ensure_login()
        return DeviceSettings.model_validate(
            self._get(
                "/api/client/customize/info", payload={"deviceId": device_id}
            )
        )

    def get_device_modes(self, home_id: str) -> list[DeviceMode]:
        """Get the operating mode of every device of a home.

        Args:
            home_id: The home ID.

        Returns:
            One DeviceMode per device.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get device modes for home %s", home_id)
        self._ensure_login()
        return _DEVICE_MODE_LIST.validate_python(
            self._get(
                "/api/client/v2/home/device/mode", payload={"homeId": home_id}
            )
        )

    def get_power_limit(self, device_id: str) -> float:
        """Get the main grid connection limit of a three-phase device.

        Shown as "main power connection limit" in the installer app.

        Args:
            device_id: The device ID.

        Returns:
            The power limit as returned by the API (0 when no limit is set).

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get power limit for device %s", device_id)
        self._ensure_login()
        value = self._get(
            "/api/client/v2/device/three/device/power_limit",
            payload={"deviceId": device_id},
        )
        return _POWER_LIMIT.validate_python(value) or 0.0

    def _get_forecast(
        self, kind: str, home_id: str, day: datetime, realtime: bool
    ) -> Forecast:
        """Get a PV or load forecast (shared implementation)."""
        logger.info("Get %s forecast for home %s", kind, home_id)
        self._ensure_login()
        path = f"/api/client/v2/home/device/insight/{kind}/forecast"
        if realtime:
            path += "/rt"
        try:
            return Forecast.model_validate(
                self._get(
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
            raise

    def get_pv_forecast(
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
            ParameterVerificationFailedError: If the day is not available (e.g. a future day with `realtime`).
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        return self._get_forecast("pv", home_id, day, realtime)

    def get_load_forecast(
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
            ParameterVerificationFailedError: If the day is not available.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        return self._get_forecast("load", home_id, day, realtime)

    def get_cost_info(self, home_id: str) -> CostInfo:
        """Get the costs and savings of a home as computed by the ECOS cloud.

        Args:
            home_id: The home ID.

        Returns:
            Savings of today, of the last days and of the current month.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get cost info for home %s", home_id)
        self._ensure_login()
        return CostInfo.model_validate(
            self._get(
                "/api/client/v2/home/cost/info", payload={"homeId": home_id}
            )
        )

    def get_week_energy(self, home_id: str) -> WeekEnergy:
        """Get the energy of the last seven days as shown on the home screen of the ECOS app.

        Args:
            home_id: The home ID.

        Returns:
            Energy per weekday and totals of the last seven days.

        Raises:
            HomeDoesNotExistError: If the home id is not correct.
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get week energy for home %s", home_id)
        self._ensure_login()
        try:
            return WeekEnergy.model_validate(
                self._get(
                    "/api/client/v2/home/device/energy", payload={"homeId": home_id}
                )
            )
        except ApiResponseError as err:
            if err.code == 20450:
                raise HomeDoesNotExistError(home_id) from err
            raise

    def get_backup_statistics(
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
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get backup statistics for device %s", device_id)
        self._ensure_login()
        return BackupStatistics.model_validate(
            self._post(
                "/api/client/home/events/backup/statistics",
                payload={
                    "deviceId": device_id,
                    "startTime": int(start_date.timestamp()),
                    "endTime": int(end_date.timestamp()),
                },
            )
        )

    def get_unread_message_count(self) -> MessageCount:
        """Get the number of unread messages of the account.

        Returns:
            Unread device and official messages.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get unread message count")
        self._ensure_login()
        return MessageCount.model_validate(
            self._post("/api/client/message/count_unread")
        )

    def get_fixed_price(self, home_id: str) -> FixedPrice | None:
        """Get the fixed electricity price configured for a home.

        Args:
            home_id: The home ID.

        Returns:
            The configured prices, or None if no fixed price is set.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get fixed price for home %s", home_id)
        self._ensure_login()
        data = self._get(
            "/api/client/ele/price/fixed/get", payload={"homeId": home_id}
        )
        return FixedPrice.model_validate(data) if data else None

    @staticmethod
    def _weather_location(longitude: float, latitude: float) -> dict[str, str]:
        # The weather service takes "longitude,latitude"; without it the API answers
        # 403, and swapped it returns empty values. Two decimals (about 1 km) are
        # enough for weather and keep the request less precise than the home.
        return {"location": f"{longitude:.2f},{latitude:.2f}"}

    def get_weather_now(self, longitude: float, latitude: float) -> WeatherNow:
        """Get the current weather at a location, as shown in the ECOS app.

        Args:
            longitude: Longitude of the location in degrees.
            latitude: Latitude of the location in degrees.

        Returns:
            The current weather; every field is None if the location is unknown
            to the weather service (e.g. longitude and latitude swapped).

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get current weather")
        self._ensure_login()
        return WeatherNow.model_validate(
            self._get(
                "/api/client/home/weather/now",
                payload=self._weather_location(longitude, latitude),
            )
        )

    def get_weather_hourly(
        self, longitude: float, latitude: float
    ) -> list[WeatherHour]:
        """Get the hourly weather forecast for the next 24 hours at a location.

        Args:
            longitude: Longitude of the location in degrees.
            latitude: Latitude of the location in degrees.

        Returns:
            One entry per hour, empty if the location is unknown to the weather service.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get hourly weather forecast")
        self._ensure_login()
        return _WEATHER_HOURS.validate_python(
            self._get(
                "/api/client/home/weather/24h",
                payload=self._weather_location(longitude, latitude),
            )
        )

    def get_weather_daily(
        self, longitude: float, latitude: float
    ) -> list[WeatherDay]:
        """Get the daily weather forecast for the next 7 days at a location.

        Args:
            longitude: Longitude of the location in degrees.
            latitude: Latitude of the location in degrees.

        Returns:
            One entry per day, empty if the location is unknown to the weather service.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.

        """
        logger.info("Get daily weather forecast")
        self._ensure_login()
        return _WEATHER_DAYS.validate_python(
            self._get(
                "/api/client/home/weather/7d",
                payload=self._weather_location(longitude, latitude),
            )
        )
