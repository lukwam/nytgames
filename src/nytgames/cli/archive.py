"""nytg archive: save puzzles as JSON files, one per date."""
import enum
import json
import time
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from rich.progress import BarColumn
from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import TextColumn
from rich.progress import TimeRemainingColumn

from nytgames import NYTGamesAuthenticationError
from nytgames import NYTGamesClient
from nytgames import NYTGamesHTTPError
from nytgames import NYTGamesNotFoundError
from nytgames.cli.dates import date_range
from nytgames.cli.output import FormatOption
from nytgames.cli.output import emit
from nytgames.cli.output import err_console
from nytgames.cli.output import key_value_table
from nytgames.cli.state import date_arg
from nytgames.cli.state import state


class ArchiveGame(str, enum.Enum):
    wordle = "wordle"
    connections = "connections"
    strands = "strands"
    spelling_bee = "spelling-bee"
    letter_boxed = "letter-boxed"
    crossword_daily = "crossword-daily"
    crossword_mini = "crossword-mini"
    crossword_midi = "crossword-midi"


def fetcher(client: NYTGamesClient, game: ArchiveGame):
    """Return a function that fetches the game's puzzle for a date."""
    if game.value.startswith("crossword-"):
        kind = game.value.split("-", 1)[1]
        return lambda day: client.crossword(kind, day)
    return {
        ArchiveGame.wordle: client.wordle,
        ArchiveGame.connections: client.connections,
        ArchiveGame.strands: client.strands,
        ArchiveGame.spelling_bee: client.spelling_bee_puzzle,
        ArchiveGame.letter_boxed: client.letter_boxed,
    }[game]


def archive(
    game: Annotated[ArchiveGame, typer.Argument(help="The game to archive.")],
    start: Annotated[str, typer.Option("--from", help='First date, or "first" for the first puzzle.')] = "today",
    end: Annotated[str, typer.Option("--to", help="Last date.")] = "today",
    out: Annotated[Path, typer.Option("--out", "-o", help="Directory to save into.", file_okay=False)] = Path("nyt-archive"),
    delay: Annotated[float, typer.Option(help="Seconds to wait between requests.", min=0)] = 0.25,
    overwrite: Annotated[bool, typer.Option(help="Download dates that are already saved.")] = False,
    fmt: FormatOption = None,
) -> None:
    """Save each date's puzzle as JSON in OUT/GAME/YYYY-MM-DD.json.

    Dates already saved are skipped, so an interrupted archive can be resumed
    by running the same command again. Dates without a puzzle are reported as
    missing.
    """
    first = date_arg(start, game.value)
    last = date_arg(end, game.value)
    if first > last:
        raise typer.BadParameter("--from is after --to")
    directory = out / game.value
    directory.mkdir(parents=True, exist_ok=True)
    fetch = fetcher(state.client(), game)
    days = list(date_range(first, last))
    result: dict[str, Optional[object]] = {"game": game.value, "directory": str(directory),
                                           "saved": 0, "skipped": 0, "missing": [], "errors": []}
    columns = (TextColumn("{task.description}"), BarColumn(), MofNCompleteColumn(), TimeRemainingColumn())
    with Progress(*columns, console=err_console, transient=True) as progress:
        task = progress.add_task(f"Archiving {game.value}", total=len(days))
        for day in days:
            path = directory / f"{day}.json"
            if path.exists() and not overwrite:
                result["skipped"] += 1
                progress.advance(task)
                continue
            try:
                puzzle = fetch(day.isoformat())
            except NYTGamesAuthenticationError:
                raise
            except NYTGamesNotFoundError:
                result["missing"].append(day.isoformat())
            except NYTGamesHTTPError as err:
                result["errors"].append({"date": day.isoformat(), "error": str(err)})
            else:
                data = puzzle.model_dump(mode="json", by_alias=True)
                tmp = path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
                tmp.replace(path)
                result["saved"] += 1
            progress.advance(task)
            if delay:
                time.sleep(delay)

    def table(data):
        yield key_value_table({
            "Saved": data["saved"],
            "Already saved": data["skipped"],
            "No puzzle": ", ".join(data["missing"]) if len(data["missing"]) <= 5
            else f"{len(data['missing'])} dates",
            "Errors": len(data["errors"]),
            "Directory": data["directory"],
        }, title=f"[bold]Archived {data['game']}[/bold]")

    emit(result, fmt, table)
    if result["errors"]:
        raise typer.Exit(1)
