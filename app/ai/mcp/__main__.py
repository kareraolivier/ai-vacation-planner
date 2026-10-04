"""Run the travel MCP server over stdio for external MCP hosts.

    python -m app.ai.mcp
"""

from .server import create_fastmcp_server


def main() -> None:
    mcp = create_fastmcp_server()
    mcp.run()


if __name__ == "__main__":
    main()
