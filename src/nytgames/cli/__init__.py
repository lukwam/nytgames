"""nytg: the NYT Games command line.

Requires the `cli` extra::

    pip install "nytimes-games[cli]"

To build your own command line on top of nytg, use the public API in
``nytgames.cli.extension``: ``create_app()``, ``run()``, ``emit()``,
``FormatOption`` and ``get_client()``. ``create_app`` and ``run`` can also be
imported from here.
"""
from typing import Any

_EXTENSION_NAMES = {"create_app", "run"}


def _missing_extra(err: ImportError) -> SystemExit:
    return SystemExit(
        f'nytg needs the cli extra ({err.name} is missing). Install it with:\n'
        '    pip install "nytimes-games[cli]"'
    )


def main() -> None:
    """Entry point for the nytg command."""
    try:
        from nytgames.cli.app import main as run_nytg
    except ImportError as err:
        raise _missing_extra(err) from None
    run_nytg()


def __getattr__(name: str) -> Any:
    """Import create_app and run lazily, so the base install doesn't need Typer."""
    if name in _EXTENSION_NAMES:
        from nytgames.cli import extension

        return getattr(extension, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
