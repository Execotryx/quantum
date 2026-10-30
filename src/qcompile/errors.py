class ValidationError(ValueError):
    """Invalid input or evidence; the diagnostic is intended for operators."""


class BlockedError(ValidationError):
    """A required contract or execution prerequisite is unavailable."""
