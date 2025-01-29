"""Ecos client custom exceptions."""


class EcosApiError(Exception):
    """Base exception class for all ECOS API-related errors."""


class InvalidJsonError(EcosApiError):
    """Raised when the API returns invalid JSON."""

    def __init__(self) -> None:
        super().__init__("Invalid JSON")


class ApiResponseError(EcosApiError):
    """Raised when the API returns a non-successful response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"API call failed: {code} {message}")


class HttpError(EcosApiError):
    """Raised when an HTTP error occurs while making an API request."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP error: {status_code} {message}")
