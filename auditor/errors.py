"""Validation failures for an invented task folder."""


class TaskValidationError(Exception):
    """A task folder is missing a file or has a bad field value."""

    def __init__(self, field: str, message: str, value: object = None) -> None:
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message} (value: {value!r})")
