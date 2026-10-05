"""Entry point for nytg-mcp, with a clear message when the mcp extra is missing."""


def main() -> None:
    """Run the nytimes-games MCP server over stdio."""
    try:
        from nytgames.mcp_server import main as run
    except ImportError as err:
        raise SystemExit(
            f"nytg-mcp needs the mcp extra ({err.name or 'mcp'} is missing). Install it with:\n"
            '    pip install "nytimes-games[mcp]"'
        ) from None
    run()
