class PaiHubException(Exception):
    pass


class PaiHubSystemExit(PaiHubException):
    pass


class BadRequest(PaiHubException):
    message: str

    def __init__(self, message):
        self.message = message
