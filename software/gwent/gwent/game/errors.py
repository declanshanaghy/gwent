
class GwentError(Exception):
    def __init__(self, message: str):
        self.message = message

class InvalidFactionError(GwentError):
    pass
