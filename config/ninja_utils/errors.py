class NinjaError(Exception):
    def __init__(self, error_name: str, message: str, status_code: int = 400):
        assert " " not in error_name

        self.error_name = error_name
        self.message = str(message)
        self.status_code = status_code
