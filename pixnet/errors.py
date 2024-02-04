from typing import Any, Optional, Dict, Union, Tuple, Type, NoReturn


class PixNetException(Exception):
    """Base class for PixNet errors."""


class NetworkError(PixNetException):
    """Base class for exceptions due to networking errors."""


class TimedOut(NetworkError):
    """Raised when a request took too long to finish."""


class BadRequest(PixNetException):
    """Raised when an API request cannot be processed correctly.

    :var status_code: The status code of the response.
    :var original: The original error message of the response.
    :var message: The formatted error message of the response.
    """

    status_code: int = 200
    original: str = ""
    message: str = ""

    def __init__(
        self,
        response: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        if response is not None:
            error = response.get("error")
            if error:
                response_message = response.get("message")
                if response_message is not None:
                    self.original = response_message
        if message is not None or self.original is not None:
            self.message = message or self.original

        super().__init__(self.message)

    def __repr__(self) -> str:
        response = {
            "status_code": self.status_code,
            "message": self.original,
        }
        return f"{type(self).__name__}({repr(response)})"

    @property
    def response(self) -> Dict[str, Union[str, Any, None]]:
        return {"message": self.original}


class NotSupported(BadRequest):
    """API not supported."""

    original = "API not supported or has been removed."


class TooManyRequest(BadRequest):

    original = "too many request."
