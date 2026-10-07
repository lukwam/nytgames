"""nytg bonus: the weekly Bonus Puzzles.

Answers are hidden unless --answers is given, in every output format.
"""
import enum
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from rich.table import Table
from rich.text import Text

from nytgames import views
from nytgames.cli import puzzles
from nytgames.cli.output import FormatOption
from nytgames.cli.output import emit
from nytgames.cli.output import err_console
from nytgames.cli.puzzles import AnswersOption
from nytgames.cli.state import date_arg
from nytgames.cli.state import state

WeekArgument = Annotated[
    str, typer.Argument(help="Any day in the week: YYYY-MM-DD, today, yesterday or a weekday.", show_default=True),
]


def register(app: typer.Typer) -> None:
    """Add the bonus commands to the root app."""
    bonus = typer.Typer(help="The weekly Bonus Puzzles, out on Wednesdays.", no_args_is_help=True)
    bonus.command("week")(week)
    bonus.command("wordle-in-one")(wordle_in_one)
    bonus.command("connections")(connections)
    bonus.command("strands")(strands)
    bonus.command("crossword")(crossword)
    app.add_typer(bonus, name="bonus")


def fetch_week(date: str):
    return state.client().bonus_week(date_arg(date).isoformat())


def find(date: str, kind: str, name: str | None = None):
    """Return the listing for a kind of bonus puzzle in the week's drop."""
    drop = fetch_week(date)
    listing = views.find_bonus_listing(drop, kind)
    if listing is None:
        err_console.print(f"No {name or kind} puzzle in the week of {drop.drop_date}.")
        raise typer.Exit(1)
    return listing


def week(date: WeekArgument = "today", fmt: FormatOption = None) -> None:
    """List a week's Bonus Puzzles."""
    data = views.bonus_week_view(fetch_week(date))

    def table(data):
        t = Table(title=f"Bonus Puzzles, week of {data['drop_date']}" + (" (free)" if data["free"] else ""),
                  title_justify="left", header_style="bold")
        for column in ("Puzzle", "", "By", "ID"):
            t.add_column(column)
        for p in data["puzzles"]:
            t.add_row(p["title"], Text(p["subtitle"] or "", style="dim"), (p["byline"] or "").removeprefix("By "),
                      str(p["id"]))
        yield t

    emit(data, fmt, table)


def wordle_in_one(date: WeekArgument = "today", answers: AnswersOption = False, fmt: FormatOption = None) -> None:
    """Show Wordle in 1: each round's starting guess, and the solutions with --answers."""
    listing = find(date, "wordle-in-one")
    data = views.bonus_puzzle_view(listing, state.client().bonus_puzzle(listing), answers)

    def table(data):
        yield Text(f"{data['title']} {data['date']}", style="bold")
        t = Table(show_header=False, box=None)
        for i, r in enumerate(data["rounds"]):
            t.add_row(f"{i + 1}", puzzles.tiles(r["start"], "bold white on grey37"),
                      *([puzzles.tiles(r["solution"])] if "solution" in r else []))
        yield t

    emit(data, fmt, table)


def connections(date: WeekArgument = "today", answers: AnswersOption = False, fmt: FormatOption = None) -> None:
    """Show Connections 3x3: the board, or the groups with --answers."""
    listing = find(date, "connections")
    emit(views.bonus_puzzle_view(listing, state.client().bonus_puzzle(listing), answers), fmt,
         puzzles.connections_table)


def strands(date: WeekArgument = "today", answers: AnswersOption = False, fmt: FormatOption = None) -> None:
    """Show Colorful Strands: the theme and board, and the words with --answers."""
    listing = find(date, "strands")
    emit(views.bonus_puzzle_view(listing, state.client().bonus_puzzle(listing), answers), fmt,
         puzzles.strands_table)


class BonusCrossword(str, enum.Enum):
    mini = "mini"
    easy = "easy"
    special = "special"


def crossword(
    kind: Annotated[BonusCrossword, typer.Argument(help="mini (Mystery Mini), easy or special.")]
    = BonusCrossword.mini,
    date: WeekArgument = "today",
    answers: AnswersOption = False,
    clues: Annotated[bool, typer.Option(help="Show the clues.")] = True,
    save: Annotated[
        Optional[Path],
        typer.Option("--save", "-o", help="Save as a crossword file: .puz, .ipuz or .xml (Crossword Compiler).",
                     dir_okay=False),
    ] = None,
    progress: Annotated[bool, typer.Option("--progress", help="Include your saved progress in --save.")] = False,
    fmt: FormatOption = None,
) -> None:
    """Show a bonus crossword: the Mystery Mini, Easy Mode or Special Crossword.

    With --save, write it to a file for other crossword apps instead.
    """
    listing = find(date, kind.value, f"{kind.value} crossword")
    puzzles.crossword(puzzles.CrosswordType.bonus, "today", answers, clues, save, progress, listing.id, fmt)
