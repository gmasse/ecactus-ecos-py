"""Base class for interacting with the ECOS API."""

import json
import logging
from typing import Any

from .exceptions import (
    ApiResponseError,
    HttpError,
    InitializationError,
    InvalidJsonError,
    UnauthorizedError,
)

# `requests` and `aiohttp` are imported lazily in the methods below: both HTTP
# implementations share this class, so a caller using only the synchronous mode
# never pays the import cost of `aiohttp`, and vice versa.

# Configure logging
logger = logging.getLogger(__name__)

JSON = Any

# Raw response bodies, live tokens and personal data included. The library sets
# this logger to WARNING so that a root or `ecactus` logger at DEBUG does not turn
# it on: enabling it means naming it, `logging.getLogger("ecactus.wire")`.
wire_logger = logging.getLogger("ecactus.wire")
wire_logger.setLevel(logging.WARNING)

# Response keys whose value is masked in the `ecactus` debug log. A sensitive
# key the API adds later goes through in clear until it is listed here.
_TOKEN_KEYS = frozenset({"accessToken", "refreshToken"})
_PERSONAL_KEYS = frozenset(
    {"password", "email", "phone", "username", "lat", "lon", "latitude", "longitude"}
)


def _redact(value: JSON) -> JSON:
    """Return a copy of a decoded JSON body with its sensitive values masked.

    A token keeps its last 4 characters, so that a debugging session can still
    tell whether it changed after a login.
    """
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if not isinstance(value, dict):
        return value
    redacted: dict[str, JSON] = {}
    for key, item in value.items():
        if key in _TOKEN_KEYS and isinstance(item, str) and len(item) > 8:
            redacted[key] = "…" + item[-4:]
        elif key in _TOKEN_KEYS or key in _PERSONAL_KEYS:
            redacted[key] = "<REDACTED>"
        else:
            redacted[key] = _redact(item)
    return redacted


def _log_response(method: str, api_path: str, status: int, text: str) -> None:
    """Log a response: raw to `ecactus.wire`, redacted to the module logger."""
    wire_logger.debug("%s /%s -> HTTP %s: %s", method, api_path, status, text)
    if not logger.isEnabledFor(logging.DEBUG):
        return
    try:
        body: JSON = _redact(json.loads(text))
    except ValueError:
        body = f"<non-JSON body, {len(text)} characters>"
    logger.debug("%s /%s -> HTTP %s: %s", method, api_path, status, body)


class _BaseEcos:
    """Base class for interacting with the ECOS API."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        country: str | None = None,
        datacenter: str | None = None,
        url: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        timeout: float | None = 30.0,
    ) -> None:
        """Initialize a session with ECOS API.

        Args:
            email: The user's email to use for authentication.
            password: The user's password to use for authentication.
            country: _Reserved for future_.
            datacenter: The location of the ECOS API datacenter.
                Can be one of `CN`, `EU`, or `AU`.
            url: The URL of the ECOS API. If specified, `datacenter` is ignored.
            access_token: The access token for authentication with the ECOS API.
            refresh_token: The refresh token for authentication with the ECOS API.
            timeout: Per-request timeout in seconds (total). Applied to every HTTP
                call. `None` disables the timeout. Defaults to 30 seconds.

        Raises:
            InitializationError: If `datacenter` is not one of `CN`, `EU`, or `AU` and `url` is not provided.

        """
        logger.info("Initializing session")
        self.email = email
        self.password = password
        self.country = country
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.timeout = timeout
        # TODO: get datacenters from https://dcdn-config.weiheng-tech.com/prod/config.json
        datacenters = {
            "CN": "https://api-ecos-hu.weiheng-tech.com",
            "EU": "https://api-ecos-eu.weiheng-tech.com",
            "AU": "https://api-ecos-au.weiheng-tech.com",
        }
        if url is None:
            if datacenter is None:
                raise InitializationError("url or datacenter not specified")
            if datacenter not in datacenters:
                raise InitializationError(
                    "datacenter must be one of {}".format(", ".join(datacenters.keys()))
                )
            self.url = datacenters[datacenter]
        else:  # url specified, ignore datacenter
            self.url = url.rstrip("/")  # remove trailing / from url

    def _get(self, api_path: str, payload: dict[str, Any] = {}) -> JSON:
        """Make a GET request to the ECOS API.

        Args:
            api_path: The path of the API endpoint.
            payload: The data to be sent with the request.

        Returns:
            JSON: The data returned by the API.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            HttpError: For HTTP error not related to API.
            InvalidJsonError: If the API returns an invalid JSON.

        """
        import requests  # noqa: PLC0415

        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.debug("API GET call: %s", full_url)
        headers = (
            {"Authorization": self.access_token}
            if self.access_token is not None
            else None
        )
        response = None
        try:
            response = requests.get(
                full_url, params=payload, headers=headers, timeout=self.timeout
            )
            _log_response("GET", api_path, response.status_code, response.text)
            body = response.json()
        except requests.exceptions.JSONDecodeError as err:
            if response and response.status_code != 200:
                raise HttpError(response.status_code, response.text) from err
            raise InvalidJsonError from err
        else:
            if not response.ok:
                error_msg = body.get(
                    "message", response.text
                )  # return message from JSON if avalaible, or HTTP response text
                if body.get("code") == 401:
                    raise UnauthorizedError(error_msg)
                if body.get("code") is not None:
                    raise ApiResponseError(body.get("code"), error_msg)
                raise HttpError(response.status_code, error_msg)
            if not body.get("success"):
                raise ApiResponseError(body.get("code"), body.get("message"))
        return body.get("data")

    def _post(self, api_path: str, payload: JSON = {}) -> JSON:
        """Make a POST request to the ECOS API.

        Args:
            api_path: The path of the API endpoint.
            payload: The data to be sent with the request.

        Returns:
            JSON: The data returned by the API.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            HttpError: For HTTP error not related to API.
            InvalidJsonError: If the API returns an invalid JSON.

        """
        import requests  # noqa: PLC0415

        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.debug("API POST call: %s", full_url)
        headers = (
            {"Authorization": self.access_token}
            if self.access_token is not None
            else None
        )
        response = None
        try:
            response = requests.post(
                full_url, json=payload, headers=headers, timeout=self.timeout
            )
            _log_response("POST", api_path, response.status_code, response.text)
            body = response.json()
        except requests.exceptions.JSONDecodeError as err:
            if response and response.status_code != 200:
                raise HttpError(response.status_code, response.text) from err
            raise InvalidJsonError from err
        else:
            if not response.ok:
                error_msg = body.get(
                    "message", response.text
                )  # return message from JSON if avalaible, or HTTP response text
                if body.get("code") == 401:
                    raise UnauthorizedError(error_msg)
                if body.get("code") is not None:
                    raise ApiResponseError(body.get("code"), error_msg)
                raise HttpError(response.status_code, error_msg)
            if not body.get("success"):
                raise ApiResponseError(body.get("code"), body.get("message"))
        return body.get("data")

    async def _async_get(self, api_path: str, payload: dict[str, Any] = {}) -> JSON:
        """Make a GET request to the ECOS API.

        Args:
            api_path: The path of the API endpoint.
            payload: The data to be sent with the request.

        Returns:
            JSON: The data returned by the API.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            HttpError: For HTTP error not related to API.
            InvalidJsonError: If the API returns an invalid JSON.

        """
        import aiohttp  # noqa: PLC0415

        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.debug("API GET call: %s", full_url)

        headers = (
            {"Authorization": self.access_token}
            if self.access_token is not None
            else None
        )
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = None
            try:
                async with session.get(
                    full_url, params=payload, headers=headers
                ) as response:
                    _log_response(
                        "GET", api_path, response.status, await response.text()
                    )
                    body = await response.json()
            except aiohttp.ContentTypeError as err:
                if response and response.status != 200:
                    raise HttpError(response.status, await response.text()) from err
                raise InvalidJsonError from err
            else:
                if response and response.status != 200:
                    error_msg = body.get(
                        "message", await response.text()
                    )  # return message from JSON if avalaible, or HTTP response text
                    if body.get("code") == 401:
                        raise UnauthorizedError(error_msg)
                    if body.get("code") is not None:
                        raise ApiResponseError(body.get("code"), error_msg)
                    raise HttpError(response.status, error_msg)
                if not body.get("success"):
                    raise ApiResponseError(body.get("code"), body.get("message"))
        return body.get("data")

    async def _async_post(self, api_path: str, payload: JSON = {}) -> JSON:
        """Make a POST request to the ECOS API.

        Args:
            api_path: The path of the API endpoint.
            payload: The data to be sent with the request.

        Returns:
            JSON: The data returned by the API.

        Raises:
            UnauthorizedError: If the Authorization token is not valid.
            ApiResponseError: If the API returns a non-successful response.
            HttpError: For HTTP error not related to API.
            InvalidJsonError: If the API returns an invalid JSON.

        """
        import aiohttp  # noqa: PLC0415

        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.debug("API POST call: %s", full_url)

        headers = (
            {"Authorization": self.access_token}
            if self.access_token is not None
            else None
        )
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = None
            try:
                async with session.post(
                    full_url, json=payload, headers=headers
                ) as response:
                    _log_response(
                        "POST", api_path, response.status, await response.text()
                    )
                    body = await response.json()
            except aiohttp.ContentTypeError as err:
                if response and response.status != 200:
                    raise HttpError(response.status, await response.text()) from err
                raise InvalidJsonError from err
            else:
                if response and response.status != 200:
                    error_msg = body.get(
                        "message", await response.text()
                    )  # return message from JSON if avalaible, or HTTP response text
                    if body.get("code") == 401:
                        raise UnauthorizedError(error_msg)
                    if body.get("code") is not None:
                        raise ApiResponseError(body.get("code"), error_msg)
                    raise HttpError(response.status, error_msg)
                if not body.get("success"):
                    raise ApiResponseError(body.get("code"), body.get("message"))
        return body.get("data")
