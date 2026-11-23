"""Base class for interacting with the ECOS API."""

from collections.abc import AsyncIterable, Iterable
import ipaddress
import json
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from .exceptions import (
    ApiResponseError,
    HttpError,
    InitializationError,
    InvalidJsonError,
    UnauthorizedError,
)

if TYPE_CHECKING:
    import requests

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

# Response keys whose value is masked in the `ecactus` debug log, compared
# case-insensitively. A key containing a secret marker, or named in the personal
# list, is masked whole; one containing "token", or named "authorization", is a
# token. Any other key goes through in clear: a sensitive field the API adds later
# (a personal one, or a credential such as `apiKey` or `sessionId`) is logged as
# is until it is listed here. Home and device IDs stay in clear on purpose: the
# INFO log names them anyway, and a debugging session needs them.
_SECRET_MARKERS = ("password", "secret")
_PERSONAL_KEYS = frozenset(
    {
        "email",
        "phone",
        "username",
        "nickname",
        "homename",
        "devicealiasname",
        "devicesn",
        "wifisn",
        "lat",
        "lon",
        "latitude",
        "longitude",
    }
)


def _redact_item(key: str, item: JSON) -> JSON:
    """Return the value of a JSON object member, masked if its key is sensitive.

    A token keeps its last 4 characters, so that a debugging session can still
    tell whether it changed after a login.
    """
    name = key.casefold()
    if name in _PERSONAL_KEYS or any(marker in name for marker in _SECRET_MARKERS):
        return "<REDACTED>"
    if "token" in name or name == "authorization":
        if isinstance(item, str) and len(item) > 8:
            return "…" + item[-4:]
        return "<REDACTED>"
    return _redact(item)


def _redact(value: JSON) -> JSON:
    """Return a copy of a decoded JSON body with its sensitive values masked."""
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {key: _redact_item(key, item) for key, item in value.items()}


def _log_response(method: str, api_path: str, status: int, text: str) -> None:
    """Log a response: raw to `ecactus.wire`, redacted to the module logger."""
    wire_logger.debug("%s /%s -> HTTP %s: %s", method, api_path, status, text)
    if not logger.isEnabledFor(logging.DEBUG):
        return
    try:
        body: JSON = _redact(json.loads(text))
    except (ValueError, RecursionError):  # invalid, or nested too deep
        body = f"<undecodable body, {len(text)} characters>"
    logger.debug("%s /%s -> HTTP %s: %s", method, api_path, status, body)


# A response larger than this raises InvalidJsonError instead of filling memory.
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
_CHUNK_SIZE = 64 * 1024


def _too_large() -> InvalidJsonError:
    return InvalidJsonError(f"Response larger than {MAX_RESPONSE_BYTES} bytes")


def _read_limited(chunks: Iterable[bytes]) -> bytes:
    """Read a response body, up to MAX_RESPONSE_BYTES."""
    body = bytearray()
    for chunk in chunks:
        body += chunk
        if len(body) > MAX_RESPONSE_BYTES:
            raise _too_large()
    return bytes(body)


async def _async_read_limited(chunks: AsyncIterable[bytes]) -> bytes:
    """Read a response body, up to MAX_RESPONSE_BYTES."""
    body = bytearray()
    async for chunk in chunks:
        body += chunk
        if len(body) > MAX_RESPONSE_BYTES:
            raise _too_large()
    return bytes(body)


def _decode(body: bytes, charset: str | None) -> str:
    """Decode a response body with its declared charset, UTF-8 by default."""
    try:
        return body.decode(charset or "utf-8", errors="replace")
    except LookupError:  # a charset Python does not know
        return body.decode("utf-8", errors="replace")


def _decode_object(text: str) -> dict[str, JSON] | None:
    """Return the JSON object in `text`, or None if it holds anything else."""
    try:
        body = json.loads(text)
    except (ValueError, RecursionError):  # invalid, or nested too deep
        return None
    return body if isinstance(body, dict) else None


def _parse_response(status: int, text: str) -> JSON:
    """Return the `data` of an ECOS API response, or raise the matching error.

    Raises:
        UnauthorizedError: If the Authorization token is not valid.
        ApiResponseError: If the API returns a non-successful response.
        HttpError: For HTTP error not related to API, a redirect included.
        InvalidJsonError: If the API returns an invalid JSON.

    """
    if 300 <= status < 400:
        # Redirects are not followed: whatever its body, a 3xx is an error.
        raise _redirect_error(status)
    body = _decode_object(text)
    if body is None:
        if status != 200:
            raise HttpError(status, text)
        raise InvalidJsonError
    if status >= 400:
        # message from JSON if available, or HTTP response text
        error_msg = body.get("message", text)
        if body.get("code") == 401:
            raise UnauthorizedError(error_msg)
        if body.get("code") is not None:
            raise ApiResponseError(body.get("code"), error_msg)
        raise HttpError(status, error_msg)
    if not body.get("success"):
        raise ApiResponseError(body.get("code"), body.get("message"))
    return body.get("data")


def _redirect_error(status: int) -> HttpError:
    return HttpError(status, "Redirect not followed")


def _reject_redirect(response: "requests.Response", **kwargs: Any) -> None:
    """Raise on a redirect before `requests` reads its body (a response hook).

    Even with `allow_redirects=False`, `requests` reads the whole body of a
    redirect to prepare `Response.next`, outside of the MAX_RESPONSE_BYTES limit.
    """
    if response.is_redirect:
        response.close()
        raise _redirect_error(response.status_code)


def _is_loopback(host: str | None) -> bool:
    """Tell whether a URL host is `localhost` or a loopback IP address."""
    if host is None:
        return False
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:  # a host name, not an IP address
        return False


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

        The client never follows an HTTP redirect, which could carry the email and
        password to another host or to plain http: a 3xx response raises `HttpError`.

        Args:
            email: The user's email to use for authentication.
            password: The user's password to use for authentication.
            country: _Reserved for future_.
            datacenter: The location of the ECOS API datacenter.
                Can be one of `CN`, `EU`, or `AU`.
            url: The URL of the ECOS API. If specified, `datacenter` is ignored.
                Must use `https`, except on a loopback host (`localhost`, `127.0.0.1`, `::1`).
            access_token: The access token for authentication with the ECOS API.
            refresh_token: The refresh token for authentication with the ECOS API.
            timeout: Per-request timeout in seconds (total). Applied to every HTTP
                call. `None` disables the timeout. Defaults to 30 seconds.

        Raises:
            InitializationError: If `datacenter` is not one of `CN`, `EU`, or `AU` and `url` is not provided.
            InitializationError: If `url` does not use `https` and its host is not a loopback address.

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
            # Plain http would send the email and password in clear; loopback stays
            # allowed for local test servers.
            parts = urlsplit(url)
            if parts.scheme != "https" and not (
                parts.scheme == "http" and _is_loopback(parts.hostname)
            ):
                raise InitializationError(
                    "url must use https (http is only accepted on a loopback host)"
                )
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
        with requests.get(
            full_url,
            params=payload,
            headers=headers,
            timeout=self.timeout,
            stream=True,
            allow_redirects=False,
            hooks={"response": _reject_redirect},
        ) as response:
            status = response.status_code
            text = _decode(
                _read_limited(response.iter_content(_CHUNK_SIZE)), response.encoding
            )
        _log_response("GET", api_path, status, text)
        return _parse_response(status, text)

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
        with requests.post(
            full_url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
            stream=True,
            allow_redirects=False,
            hooks={"response": _reject_redirect},
        ) as response:
            status = response.status_code
            text = _decode(
                _read_limited(response.iter_content(_CHUNK_SIZE)), response.encoding
            )
        _log_response("POST", api_path, status, text)
        return _parse_response(status, text)

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
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(
                full_url, params=payload, headers=headers, allow_redirects=False
            ) as response,
        ):
            status = response.status
            text = _decode(
                await _async_read_limited(response.content.iter_chunked(_CHUNK_SIZE)),
                response.charset,
            )
        _log_response("GET", api_path, status, text)
        return _parse_response(status, text)

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
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(
                full_url, json=payload, headers=headers, allow_redirects=False
            ) as response,
        ):
            status = response.status
            text = _decode(
                await _async_read_limited(response.content.iter_chunked(_CHUNK_SIZE)),
                response.charset,
            )
        _log_response("POST", api_path, status, text)
        return _parse_response(status, text)
