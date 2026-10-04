"""nytg: the NYT Games command line.

Requires the `cli` extra::

    pip install "nytimes-games[cli]"
"""


def main() -> None:
    """Entry point for the nytg command."""
    try:
        from nytgames.cli.app import main as run
    except ImportError as err:
        raise SystemExit(
            f'nytg needs the cli extra ({err.name} is missing). Install it with:\n'
            '    pip install "nytimes-games[cli]"'
        ) from None
    run()
