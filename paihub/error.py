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


class BadRequest(PaiHubException):
    pass


class ArtWorkNotFoundError(PaiHubException):
    message = "ArtWork Not Found"


class ImagesFormatNotSupported(PaiHubException):
    pass
