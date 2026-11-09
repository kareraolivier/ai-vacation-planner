class GuardrailError(ValueError):
    """Raised when a request or model output is blocked."""

    def __init__(self, message: str, code: str = "guardrail"):
        self.code = code
        super().__init__(message)
