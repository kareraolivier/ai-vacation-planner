class MCPError(Exception):
    """User-safe MCP failure. `code` drives HTTP mapping and agent warnings."""

    def __init__(self, message: str, code: str = "provider"):
        self.code = code
        super().__init__(message)
