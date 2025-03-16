"""Implementation of a synchronous class for interacting with the ECOS API."""

from datetime import datetime
import logging
import time

from .base import _BaseEcos
from .exceptions import (
    ApiResponseError,
    AuthenticationError,
    HomeDoesNotExistError,
    ParameterVerificationFailedError,
    UnauthorizedDeviceError,
    UnauthorizedError,  # noqa: F401 # imported to make it available in the docs
)
from .model import (
    Device,
    DeviceInsight,
    EnergyHistory,
    Home,
    PowerMetrics,
    PowerTimeSeries,
    User,
)

# Configure logging
logger = logging.getLogger(__name__)


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

        """
        logger.info("Login")
        if email is not None:
            self.email = email
        if password is not None:
            self.password = password
        payload = {
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
        return User(**self._get("/api/client/settings/user/info"))

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
        return [
            Home(**home_data)
            for home_data in self._get("/api/client/v2/home/family/query")
        ]

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
            return [
                Device(**device_data)
                for device_data in self._get(
                    "/api/client/v2/home/device/query", payload={"homeId": home_id}
                )
            ]
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
        return [
            Device(**device_data)
            for device_data in self._get("/api/client/home/device/list")
        ]

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
            return PowerTimeSeries(**self._post(
                "/api/client/home/now/device/realtime", payload={"deviceId": device_id}
            ))
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
        try:
            return PowerMetrics(**self._get(
                "/api/client/v2/home/device/runData", payload={"homeId": home_id}
            ))
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
        try:
            return PowerMetrics(**self._post(
                "/api/client/home/now/device/runData", payload={"deviceId": device_id}
            ))
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
        if start_date is None:
            if period_type in (1, 2, 4):
                start_ts = 0
            else:
                raise ParameterVerificationFailedError(f"start_date is required for period_type {period_type}")
        else:
            start_ts = int(start_date.timestamp()) if start_date is not None else 0
        try:
            return EnergyHistory(**self._post(
                "/api/client/home/history/home",
                payload={
                    "deviceId": device_id,
                    "timestamp": start_ts,
                    "periodType": period_type,
                },
            ))
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
        if start_date is None:
            if period_type == 5:
                start_ts = 0
            else:
                raise ParameterVerificationFailedError(f"start_date is required for period_type {period_type}")
        else:
            start_ts = int(start_date.timestamp() * 1000)  # timestamp in milliseconds
        try:
            return DeviceInsight(**self._post(
                "/api/client/v2/device/three/device/insight",
                payload={
                    "deviceId": device_id,
                    "timestamp": start_ts,
                    "periodType": period_type,
                },
            ))
        except ApiResponseError as err:
            if err.code == 20424:
                raise UnauthorizedDeviceError(device_id) from err
            if err.code == 20404:
                raise ParameterVerificationFailedError from err
            raise
