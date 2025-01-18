# exceptions.py

class EcosApiError(Exception):
    """Base exception class for all ECOS API-related errors."""

class InvalidJsonError(EcosApiError):
    """Raised when the API returns invalid JSON."""

    def __init__(self, message, code, error):
        self.code = code
        self.error = error
        super().__init__(message)

class ApiResponseError(EcosApiError):
    """Raised when the API returns a non-successful response."""

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"API call failed: {code} {message}")

class HttpError(EcosApiError):
    """Raised when an HTTP error occurs while making an API request."""

    def __init__(self, status_code):
        self.status_code = status_code
        super().__init__(f"HTTP error: {status_code}")
