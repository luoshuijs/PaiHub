class PaiHubException(Exception):
    message: str | None = None

    def __init__(self, message: str | None = None):
        if message is not None:
            self.message = message
        if self.message is not None:
            super().__init__(message)


class PaiHubSystemExit(PaiHubException):
    pass


class ConnectionTimedOut(PaiHubException):
    pass


class RetryAfter(PaiHubException):
    def __init__(self, retry_after: int):
        super().__init__(f"Retry after {retry_after} seconds")
        self.retry_after = retry_after


class BadRequest(PaiHubException):
    pass


class ArtWorkNotFoundError(PaiHubException):
    message = "ArtWork Not Found"


class ImagesFormatNotSupported(PaiHubException):
    pass
