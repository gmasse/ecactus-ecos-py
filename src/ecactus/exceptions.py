"""Ecos client custom exceptions."""


class EcosApiError(Exception):
    """Base exception class for all ECOS API-related errors."""


class InitializationError(EcosApiError):
    """Raised when there is an initialization error."""

    def __init__(self, message: str | None = None) -> None:
        """Initialize the exception with a default error message.

        Args:
            message: The error message.

        """
        if message is None:
            super().__init__("Initialization error")
        else:
            super().__init__(message)


class AuthenticationError(EcosApiError):
    """Raised when there is an authentication error."""

    def __init__(self, message: str | None = None) -> None:
        """Initialize the exception with a default error message.

        Args:
            message: The error message.

        """
        if message is None:
            super().__init__("Account or password or country error")
        else:
            super().__init__(message)


class UnauthorizedError(EcosApiError):
    """Raised when there is an unauthorized error."""

    def __init__(self, message: str | None = None) -> None:
        """Initialize the exception with a default error message.

        Args:
            message: The error message.

        """

        if message is None:
            super().__init__("Unauthorized")
        else:
            super().__init__(message)


class HomeDoesNotExistError(EcosApiError):
    """Raised when a home does not exist."""

    def __init__(self, home_id: str | None = None) -> None:
        """Initialize the exception with a default error message.

        Args:
            home_id: The home ID the error occurred for.

        """
        if home_id is None:
            super().__init__("Home does not exist")
        else:
            super().__init__(f"Home does not exist: {home_id}")


class UnauthorizedDeviceError(EcosApiError):
    """Raised when a device is not authorized or unknown."""

    def __init__(self, device_id: str | None = None) -> None:
        """Initialize the exception with a default error message.

        Args:
            device_id: The device ID the error occurred for.

        """
        if device_id is None:
            super().__init__("Device is not authorized")
        else:
            super().__init__(f"Device is not authorized: {device_id}")


class ParameterVerificationFailedError(EcosApiError):
    """Raised when a parameter verification fails."""

    def __init__(self, message: str | None = None) -> None:
        """Initialize the exception with a default error message."""
        if message is None:
            super().__init__("Parameter verification failed")
        else:
            super().__init__(f"Parameter verification failed: {message}")


class InvalidJsonError(EcosApiError):
    """Raised when the API returns invalid JSON."""

    def __init__(self) -> None:
        """Initialize the exception with a default error message."""
        super().__init__("Invalid JSON")


class ApiResponseError(EcosApiError):
    """Raised when the API returns a non-successful response."""

    def __init__(self, code: int, message: str) -> None:
        """Initialize the exception with a default error message.

        Args:
            code: The API status code.
            message: The error message.

        """
        self.code = code
        self.message = message
        super().__init__(f"API call failed: {code} {message}")


class HttpError(EcosApiError):
    """Raised when an HTTP error occurs while making an API request."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize the exception with a default error message.

        Args:
            status_code: The HTTP status code.
            message: The error message.

        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP error: {status_code} {message}")
