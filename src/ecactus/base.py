"""Base class for interacting with the ECOS API."""

import logging
from typing import Any

from .exceptions import (
    ApiResponseError,
    HttpError,
    InitializationError,
    InvalidJsonError,
    UnauthorizedError,
)

# Configure logging
logger = logging.getLogger(__name__)

JSON = Any


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

        Raises:
            InitializationError: If `datacenter` is not one of `CN`, `EU`, or `AU` and `url` is not provided.

        """
        logger.info("Initializing session")
        self.email = email
        self.password = password
        self.country = country
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
        import requests

        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.info("API GET call: %s", full_url)
        try:
            response = requests.get(
                full_url, params=payload, headers={"Authorization": self.access_token}
            )
            logger.debug(response.text)
            body = response.json()
        except requests.exceptions.JSONDecodeError as err:
            if response.status_code != 200:
                raise HttpError(response.status_code, response.text) from err
            raise InvalidJsonError from err
        else:
            if not response.ok:
                error_msg = body.get(
                    "message", response.text
                )  # return message from JSON if avalaible, or HTTP response text
                if body["code"] == 401:
                    raise UnauthorizedError(error_msg)
                if body["code"] is not None:
                    raise ApiResponseError(body["code"], error_msg)
                raise HttpError(response.status_code, error_msg)
            if not body["success"]:
                logger.debug(body)
                raise ApiResponseError(body["code"], body["message"])
        return body["data"]

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
        import requests

        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.info("API POST call: %s", full_url)
        try:
            response = requests.post(
                full_url, json=payload, headers={"Authorization": self.access_token}
            )
            logger.debug(response.text)
            body = response.json()
        except requests.exceptions.JSONDecodeError as err:
            if response.status_code != 200:
                raise HttpError(response.status_code, response.text) from err
            raise InvalidJsonError from err
        else:
            if not response.ok:
                error_msg = body.get(
                    "message", response.text
                )  # return message from JSON if avalaible, or HTTP response text
                if body["code"] == 401:
                    raise UnauthorizedError(error_msg)
                if body["code"] is not None:
                    raise ApiResponseError(body["code"], error_msg)
                raise HttpError(response.status_code, error_msg)
            if not body["success"]:
                logger.debug(body)
                raise ApiResponseError(body["code"], body["message"])
        return body["data"]

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
        import aiohttp

        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.info("API GET call: %s", full_url)

        headers = (
            {"Authorization": self.access_token}
            if self.access_token is not None
            else None
        )
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    full_url, params=payload, headers=headers
                ) as response:
                    logger.debug(await response.text())
                    body = await response.json()
            except aiohttp.ContentTypeError as err:
                if response.status != 200:
                    raise HttpError(response.status, await response.text()) from err
                raise InvalidJsonError from err
            else:
                if response.status != 200:
                    error_msg = body.get(
                        "message", await response.text()
                    )  # return message from JSON if avalaible, or HTTP response text
                    if body["code"] == 401:
                        raise UnauthorizedError(error_msg)
                    if body["code"] is not None:
                        raise ApiResponseError(body["code"], error_msg)
                    raise HttpError(response.status, error_msg)
                if not body["success"]:
                    logger.debug(body)
                    raise ApiResponseError(body["code"], body["message"])
        return body["data"]

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
        import aiohttp

        api_path = api_path.lstrip("/")  # remove / from beginning of api_path
        full_url = self.url + "/" + api_path
        logger.info("API POST call: %s", full_url)

        headers = (
            {"Authorization": self.access_token}
            if self.access_token is not None
            else None
        )
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    full_url, json=payload, headers=headers
                ) as response:
                    logger.debug(await response.text())
                    body = await response.json()
            except aiohttp.ContentTypeError as err:
                if response.status != 200:
                    raise HttpError(response.status, await response.text()) from err
                raise InvalidJsonError from err
            else:
                if response.status != 200:
                    error_msg = body.get(
                        "message", await response.text()
                    )  # return message from JSON if avalaible, or HTTP response text
                    if body["code"] == 401:
                        raise UnauthorizedError(error_msg)
                    if body["code"] is not None:
                        raise ApiResponseError(body["code"], error_msg)
                    raise HttpError(response.status, error_msg)
                if not body["success"]:
                    logger.debug(body)
                    raise ApiResponseError(body["code"], body["message"])
        return body["data"]
