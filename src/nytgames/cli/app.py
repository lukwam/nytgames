"""nytg: the NYT Games command line."""
import sys
from typing import Annotated
from typing import Optional

import requests
import typer

from nytgames import NYTGamesAuthenticationError
from nytgames import NYTGamesNotFoundError
from nytgames import NYTGamesParseError
from nytgames import __version__
from nytgames.cli import archive
from nytgames.cli import output
from nytgames.cli import player
from nytgames.cli import puzzles
from nytgames.cli import settings
from nytgames.cli.config import Config
from nytgames.cli.state import state

app = typer.Typer(
    name="nytg",
    help="Puzzles, stats and archives from the New York Times Games.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
puzzles.register(app)
player.register(app)
app.command("archive")(archive.archive)
app.add_typer(settings.auth_app, name="auth")
app.add_typer(settings.config_app, name="config")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"nytg {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    profile: Annotated[
        Optional[str],
        typer.Option("--profile", "-p", envvar="NYTG_PROFILE", help="Profile to use for this command."),
    ] = None,
    cookies: Annotated[
        Optional[str],
        typer.Option("--cookies", help="NYT cookies for this command, e.g. NYT-S=... (or set NYT_COOKIES).",
                     show_default=False),
    ] = None,
    fmt: output.FormatOption = None,
    version: Annotated[
        bool, typer.Option("--version", callback=version_callback, is_eager=True, help="Show the version.")
    ] = False,
) -> None:
    """Puzzles, stats and archives from the New York Times Games.

    Puzzles work without logging in. For your stats and progress, run
    [bold]nytg auth login[/bold] with your NYT-S cookie, or set NYT_COOKIES.
    """
    state.config = Config()
    state.profile = profile
    state.cookies = cookies
    output.default_format = fmt or state.config.get(state.active_profile, "format")


def main() -> None:
    """Run nytg, turning NYT errors into short messages."""
    try:
        app()
    except NYTGamesAuthenticationError:
        output.err_console.print(
            "[red]NYT rejected the request.[/red] This needs your NYT cookies, which are missing "
            "or have expired. Run [bold]nytg auth login[/bold] or set NYT_COOKIES."
        )
        sys.exit(1)
    except NYTGamesNotFoundError:
        output.err_console.print("[red]Not found.[/red] NYT has no puzzle for that date.")
        sys.exit(1)
    except NYTGamesParseError as err:
        output.err_console.print(f"[red]Couldn't read NYT's response:[/red] {err}")
        sys.exit(1)
    except requests.RequestException as err:
        output.err_console.print(f"[red]Request to NYT failed:[/red] {err}")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
