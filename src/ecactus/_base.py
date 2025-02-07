"""Base class for interacting with the ECOS API."""

import logging
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

JSON = Any


class _BaseEcos:
    """Base class for interacting with the ECOS API."""

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
                Can be one of `CN`, `EU`, or `AU`. If not specified and `url` is not provided,
                a `ValueError` is raised.
            url (Optional[str]): The URL of the ECOS API. If specified, `datacenter` is ignored.
            access_token (Optional[str]): The access token for authentication with the ECOS API.
            refresh_token (Optional[str]): The refresh token for authentication with the ECOS API.

        Raises:
            ValueError: If `datacenter` is not one of `CN`, `EU`, or `AU` and `url` is not provided.

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
