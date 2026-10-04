"""nytg commands about the user: stats, today and history. These need cookies."""
import datetime
import enum
from collections.abc import Iterable
from collections.abc import Iterator
from typing import Annotated
from typing import Any
from typing import Optional

import typer
from rich.progress import Progress
from rich.table import Table
from rich.text import Text

from nytgames import NYTGamesNotFoundError
from nytgames.cli.dates import date_range
from nytgames.cli.dates import format_seconds
from nytgames.cli.dates import today as nyt_today
from nytgames.cli.output import FormatOption
from nytgames.cli.output import emit
from nytgames.cli.output import err_console
from nytgames.cli.output import key_value_table
from nytgames.cli.state import date_arg
from nytgames.cli.state import state

history_app = typer.Typer(help="Your results for a range of dates.", no_args_is_help=True)

# NYT returns game states for at most 30 puzzle IDs per request.
STATE_BATCH = 30
# NYT's crossword list returns at most 100 puzzles per request.
LIST_DAYS = 90

FromOption = Annotated[
    Optional[str], typer.Option("--from", help='First date, or "first" (default: 30 days ago).')
]
ToOption = Annotated[Optional[str], typer.Option("--to", help="Last date (default: today).")]


def register(app: typer.Typer) -> None:
    """Add the player commands to the root app."""
    app.command("stats")(stats)
    app.command("today")(today)
    app.add_typer(history_app, name="history")


def chunks(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def bar(value: int, maximum: int, width: int = 30) -> str:
    return "█" * max(1 if value else 0, round(width * value / maximum)) if maximum else ""


def percent(part: int | None, whole: int | None) -> float | None:
    return round(100 * part / whole, 1) if part is not None and whole else None


class Game(str, enum.Enum):
    all = "all"
    wordle = "wordle"
    connections = "connections"
    strands = "strands"
    bee = "bee"
    crossword = "crossword"


def summary_rows(stats) -> list[dict[str, Any]]:
    """One row per game: played, won, win rate and streaks."""
    rows = []
    if stats.wordle and stats.wordle.totalStats:
        total, calc = stats.wordle.totalStats, stats.wordle.calculatedStats
        rows.append({"game": "Wordle", "played": total.gamesPlayed, "won": total.gamesWon,
                     "current_streak": calc.currentStreak if calc else None,
                     "max_streak": calc.maxStreak if calc else None})
    if stats.connections:
        s = stats.connections
        rows.append({"game": "Connections", "played": s.puzzles_completed, "won": s.puzzles_won,
                     "current_streak": s.current_streak, "max_streak": s.max_streak})
    if stats.strands:
        s = stats.strands
        rows.append({"game": "Strands", "played": s.puzzles_started, "won": s.puzzles_completed,
                     "current_streak": s.current_streak, "max_streak": s.max_streak})
    if stats.spelling_bee:
        s = stats.spelling_bee
        rows.append({"game": "Spelling Bee", "played": s.puzzles_started, "won": s.ranks.Queen_Bee,
                     "current_streak": None, "max_streak": None})
    for name, s in (("Crossword", stats.crossword_daily), ("Mini", stats.crossword_mini),
                    ("Midi", stats.crossword_midi)):
        if s:
            streak = getattr(s, "dailyStreaks", None) or getattr(s, "streaks", None)
            rows.append({"game": name, "played": s.puzzlesStarted, "won": s.puzzlesSolved,
                         "current_streak": streak.current if streak else None,
                         "max_streak": streak.longest if streak else None})
    for row in rows:
        row["win_rate"] = percent(row["won"], row["played"])
    return rows


def stats(
    game: Annotated[Game, typer.Argument(help="A game for more detail, or all for a summary.")] = Game.all,
    fmt: FormatOption = None,
) -> None:
    """Show your stats. Spelling Bee counts Queen Bees as wins."""
    player = state.client().player_stats()
    s = player.stats
    if game == Game.all:
        data = summary_rows(s)

        def table(data):
            t = Table(title=f"NYT Games stats for user {player.user_id}", title_justify="left",
                      header_style="bold")
            for column, justify in (("Game", "left"), ("Played", "right"), ("Won", "right"),
                                    ("Win %", "right"), ("Streak", "right"), ("Max streak", "right")):
                t.add_column(column, justify=justify)
            for row in data:
                t.add_row(row["game"], str(row["played"]), str(row["won"]),
                          "" if row["win_rate"] is None else f"{row['win_rate']:g}",
                          "" if row["current_streak"] is None else str(row["current_streak"]),
                          "" if row["max_streak"] is None else str(row["max_streak"]))
            yield t

        return emit(data, fmt, table)

    model = {
        Game.wordle: s.wordle, Game.connections: s.connections, Game.strands: s.strands,
        Game.bee: s.spelling_bee, Game.crossword: s.crossword_daily,
    }[game]
    if model is None:
        err_console.print(f"No {game.value} stats yet.")
        raise typer.Exit(1)
    data = model.model_dump(mode="json", by_alias=True)
    if game == Game.crossword:
        data = {"daily": data,
                "mini": s.crossword_mini.model_dump(mode="json") if s.crossword_mini else None,
                "midi": s.crossword_midi.model_dump(mode="json") if s.crossword_midi else None}
    emit(data, fmt, {
        Game.wordle: wordle_table, Game.connections: connections_table,
        Game.strands: strands_table, Game.bee: bee_table, Game.crossword: crossword_table,
    }[game])


def distribution(title: str, counts: dict[str, int], highlight: str | None = None) -> Table:
    t = Table(title=title, title_justify="left", show_header=False, box=None)
    t.add_column(justify="right", style="bold")
    t.add_column()
    t.add_column(justify="right")
    top = max(counts.values(), default=0)
    for label, n in counts.items():
        t.add_row(label, Text(bar(n, top), style="red" if label == highlight else "green"), str(n))
    return t


def wordle_table(data):
    total = data.get("totalStats") or {}
    calc = data.get("calculatedStats") or {}
    yield key_value_table({
        "Played": total.get("gamesPlayed"), "Won": total.get("gamesWon"),
        "Win %": percent(total.get("gamesWon"), total.get("gamesPlayed")),
        "Current streak": calc.get("currentStreak"), "Max streak": calc.get("maxStreak"),
        "Last won": calc.get("lastWonPrintDate"),
    }, title="[bold]Wordle[/bold]")
    guesses = total.get("guesses") or {}
    yield distribution("Guess distribution", {k: guesses.get(k, 0) for k in ("1", "2", "3", "4", "5", "6", "fail")},
                       highlight="fail")


def connections_table(data):
    yield key_value_table({
        "Completed": data["puzzles_completed"], "Won": data["puzzles_won"],
        "Win %": percent(data["puzzles_won"], data["puzzles_completed"]),
        "Current streak": data["current_streak"], "Max streak": data["max_streak"],
    }, title="[bold]Connections[/bold]")
    yield distribution("Mistakes", {k: data["mistakes"].get(k, 0) for k in sorted(data["mistakes"])})


def strands_table(data):
    yield key_value_table({
        "Started": data["puzzles_started"], "Completed": data["puzzles_completed"],
        "Current streak": data["current_streak"], "Max streak": data["max_streak"],
        "Spangram first": data["spangram_first"], "No hints": data["no_hints"],
    }, title="[bold]Strands[/bold]")


def bee_table(data):
    longest = data.get("longest_word") or {}
    yield key_value_table({
        "Puzzles started": data["puzzles_started"], "Words found": data["total_words"],
        "Pangrams": data["total_pangrams"],
        "Longest word": f"{longest.get('word', '')} ({longest.get('print_date', '')})" if longest else None,
    }, title="[bold]Spelling Bee[/bold]")
    order = ["Beginner", "Good Start", "Moving Up", "Good", "Solid", "Nice", "Great", "Amazing",
             "Genius", "Queen Bee"]
    ranks = data.get("ranks") or {}
    yield distribution("Best rank reached", {r: ranks.get(r, 0) for r in order})


def crossword_table(data):
    daily = data["daily"]
    streak = daily.get("dailyStreaks") or {}
    yield key_value_table({
        "Started": daily["puzzlesStarted"], "Solved": daily["puzzlesSolved"],
        "Solve rate": f"{100 * daily['solveRate']:.1f}%",
        "Current streak": streak.get("current"), "Longest streak": streak.get("longest"),
    }, title="[bold]Daily crossword[/bold]")
    t = Table(header_style="bold")
    for column in ("Day", "Solves", "Average", "Best", "Best date", "This week", "Day streak"):
        t.add_column(column, justify="left" if column in ("Day", "Best date") else "right")
    for day, s in daily["dailyStats"].items():
        best = s.get("best") or {}
        t.add_row(day.title(), str(s["totalSolves"]), format_seconds(s["avgTimeSeconds"]),
                  format_seconds(best.get("timeSeconds")), best.get("date") or "",
                  format_seconds(s.get("thisWeeksTime")) if s.get("thisWeeksTime") else "",
                  str((s.get("verticalStreak") or {}).get("current", "")))
    yield t
    for name in ("mini", "midi"):
        s = data.get(name)
        if s:
            yield key_value_table({
                "Solved": f"{s['puzzlesSolved']} of {s['puzzlesStarted']}",
                "Average": format_seconds(s["avgTimeSeconds"]),
                "Best": f"{format_seconds(s.get('bestTimeSeconds'))} ({s.get('bestDate')})",
                "Streak": f"{(s.get('streaks') or {}).get('current')} (longest {(s.get('streaks') or {}).get('longest')})",
            }, title=f"[bold]{name.title()}[/bold]")


def today(fmt: FormatOption = None) -> None:
    """Show which of today's games you've played."""
    client = state.client()
    day = nyt_today().isoformat()
    player = client.player_stats()
    rows = []

    wordle_id = client.wordle(day).id
    states = client.wordle_latest(wordle_id).states
    if states:
        g = states[0].game_data
        rows.append({"game": "Wordle", "status": g.status.lower().replace("_", " "),
                     "detail": f"{g.currentRowIndex}/6" if g.status == "WIN" else ""})
    else:
        rows.append({"game": "Wordle", "status": "not played", "detail": ""})

    for name, s in (("Connections", player.stats.connections), ("Strands", player.stats.strands)):
        played = bool(s and s.last_played_print_date == day)
        rows.append({"game": name, "status": "played" if played else "not played", "detail": ""})

    bee = client.spelling_bee_puzzle(day)
    states = client.spelling_bee_latest(bee.id).states
    if states:
        g = states[0].game_data
        rows.append({"game": "Spelling Bee", "status": g.rank,
                     "detail": f"{len(g.answers)}/{len(bee.answers)} words"})
    else:
        rows.append({"game": "Spelling Bee", "status": "not played", "detail": ""})

    for kind in ("daily", "mini", "midi"):
        results = crossword_results(client, kind, datetime.date.fromisoformat(day),
                                    datetime.date.fromisoformat(day))
        if not results:
            continue
        r = results[0]
        status = ("solved" if r["solved"] else "in progress" if r["percent_filled"] else "not played")
        detail = " ".join(x for x in (format_seconds(r["seconds"]) if r["seconds"] else "",
                                      "⭐" if (r["star"] or "").lower() == "gold" else "") if x)
        rows.append({"game": "Crossword" if kind == "daily" else kind.title(), "status": status,
                     "detail": detail})

    def table(data):
        done = {"win", "solved", "played", "queen bee", "genius"}
        t = Table(title=f"Today's games ({day})", title_justify="left", header_style="bold")
        t.add_column("")
        t.add_column("Game")
        t.add_column("Status")
        t.add_column("Detail")
        for row in data:
            status = row["status"].lower()
            icon = ("[green]✔[/green]" if status in done else "[red]✘[/red]" if status == "fail"
                    else "[dim]·[/dim]" if status == "not played" else "[yellow]…[/yellow]")
            t.add_row(icon, row["game"], row["status"], row["detail"])
        yield t

    emit(rows, fmt, table)


def date_window(start: str | None, end: str | None, game: str) -> tuple[datetime.date, datetime.date]:
    last = date_arg(end, game) if end else nyt_today()
    first = date_arg(start, game) if start else last - datetime.timedelta(days=29)
    if first > last:
        raise typer.BadParameter("--from is after --to")
    return first, last


def progress(items: Iterable, total: int, description: str):
    """Show a progress bar on stderr for long runs."""
    if total <= 7:
        yield from items
        return
    with Progress(console=err_console, transient=True) as bar_:
        task = bar_.add_task(description, total=total)
        for item in items:
            yield item
            bar_.advance(task)


class CrosswordKind(str, enum.Enum):
    daily = "daily"
    mini = "mini"
    midi = "midi"
    bonus = "bonus"


def crossword_results(client, kind: str, first: datetime.date, last: datetime.date) -> list[dict]:
    """Return the user's crossword results for a date range.

    Daily, Mini and Bonus puzzles come from NYT's crossword list, 90 days at a
    time. That list doesn't include Midi puzzles, so Midi puzzles come from the
    games archive and their progress from the saved game states.
    """
    puzzles = []
    if kind == "midi":
        for puzzle in client.archive("crossword_midi", first.isoformat(), last.isoformat()):
            puzzles.append({"date": puzzle.print_date, "puzzle_id": puzzle.id,
                            "title": "", "author": puzzle.byline or ""})
    else:
        window_start = first
        while window_start <= last:
            window_end = min(window_start + datetime.timedelta(days=LIST_DAYS - 1), last)
            for item in client.crossword_puzzles(kind, sort_order="asc", sort_by="print_date",
                                                 date_start=window_start.isoformat(),
                                                 date_end=window_end.isoformat()).results:
                puzzles.append({"date": item.print_date, "puzzle_id": item.puzzle_id,
                                "title": item.title, "author": item.author, "solved": item.solved,
                                "percent_filled": item.percent_filled, "star": item.star})
            window_start = window_end + datetime.timedelta(days=1)

    games = {}
    ids = [p["puzzle_id"] for p in puzzles]
    for batch in progress(list(chunks(ids, STATE_BATCH)), len(ids) // STATE_BATCH + 1,
                          "Fetching solve times"):
        for game in client.crossword_game(batch, kind).states:
            games[int(game.puzzle_id)] = game.game_data

    rows = []
    for p in sorted(puzzles, key=lambda p: p["date"]):
        g = games.get(p["puzzle_id"])
        extra = (g.model_extra or {}) if g else {}
        if "solved" not in p:
            p["solved"] = bool(g and g.firstSolve)
            p["percent_filled"] = round(100 * (g.completionFraction or 0)) if g else 0
            p["star"] = g.star if g else None
        rows.append({
            "date": p["date"],
            "weekday": datetime.date.fromisoformat(p["date"]).strftime("%A"),
            "puzzle_id": p["puzzle_id"],
            "title": p["title"],
            "author": p["author"],
            "solved": p["solved"],
            "percent_filled": p["percent_filled"],
            "star": p["star"],
            "seconds": g.playTimeSeconds if g else None,
            "first_solve_date": g.firstSolveDate if g else None,
            "used_help": bool(extra.get("firstSolveUsedAid") or extra.get("revealed")) if g else None,
        })
    return rows


@history_app.command("crossword")
def history_crossword(
    publish_type: Annotated[CrosswordKind, typer.Argument(help="daily, mini, midi or bonus.")] = CrosswordKind.daily,
    start: FromOption = None,
    end: ToOption = None,
    fmt: FormatOption = None,
) -> None:
    """Your crossword results: solved, solve time, gold star and help used."""
    kind = publish_type.value
    first, last = date_window(start, end, f"crossword-{kind}")
    rows = crossword_results(state.client(), kind, first, last)

    def table(data):
        t = Table(title=f"{kind.title()} crosswords {first} to {last}", title_justify="left",
                  header_style="bold")
        for column in ("Date", "Day", "Author", "Solved", "Time", ""):
            t.add_column(column, justify="right" if column == "Time" else "left")
        for row in data:
            solved = ("[green]✔[/green]" if row["solved"]
                      else f"{row['percent_filled']}%" if row["percent_filled"] else "")
            t.add_row(row["date"], row["weekday"][:3], row["author"], solved,
                      format_seconds(row["seconds"]) if row["seconds"] else "",
                      "⭐" if (row["star"] or "").lower() == "gold" else "")
        yield t
        times = [r["seconds"] for r in data if r["solved"] and r["seconds"]]
        if times:
            yield Text(f"{len(times)} solved, average {format_seconds(sum(times) // len(times))},"
                       f" fastest {format_seconds(min(times))}", style="dim")

    emit(rows, fmt, table)


@history_app.command("wordle")
def history_wordle(start: FromOption = None, end: ToOption = None, fmt: FormatOption = None) -> None:
    """Your Wordle results: won or lost, and guesses."""
    client = state.client()
    first, last = date_window(start, end, "wordle")
    ids = {p.id: p.print_date for p in client.archive("wordle", first.isoformat(), last.isoformat())}
    states = {}
    for batch in chunks(list(ids), STATE_BATCH):
        for game in client.wordle_latest(batch).states:
            states[int(game.puzzle_id)] = game.game_data
    rows = []
    for puzzle_id, day in ids.items():
        g = states.get(puzzle_id)
        rows.append({
            "date": day, "puzzle_id": puzzle_id,
            "status": g.status.lower() if g else "not played",
            "guesses": g.currentRowIndex if g and g.status == "WIN" else None,
            "hard_mode": g.hardMode if g else None,
            "board": [w for w in g.boardState if w] if g else [],
        })

    def table(data):
        t = Table(title=f"Wordle {first} to {last}", title_justify="left", header_style="bold")
        for column in ("Date", "Result", "Guesses", "Words"):
            t.add_column(column)
        for row in data:
            style = {"win": "green", "fail": "red"}.get(row["status"], "dim")
            t.add_row(row["date"], Text(row["status"], style=style), str(row["guesses"] or ""),
                      " ".join(row["board"]).upper())
        yield t

    emit(rows, fmt, table)


@history_app.command("bee")
def history_bee(start: FromOption = None, end: ToOption = None, fmt: FormatOption = None) -> None:
    """Your Spelling Bee results: rank and words found."""
    client = state.client()
    first, last = date_window(start, end, "spelling-bee")
    days = list(date_range(first, last))
    puzzles = {}
    for day in progress(days, len(days), "Fetching puzzles"):
        try:
            puzzle = client.spelling_bee_puzzle(day.isoformat())
            puzzles[puzzle.id] = puzzle
        except NYTGamesNotFoundError:
            pass
    states = {}
    for batch in chunks(list(puzzles), STATE_BATCH):
        for game in client.spelling_bee_latest(batch).states:
            states[int(game.puzzle_id)] = game.game_data
    rows = []
    for puzzle_id, puzzle in puzzles.items():
        g = states.get(puzzle_id)
        found = set(g.answers) if g else set()
        rows.append({
            "date": puzzle.printDate, "puzzle_id": puzzle_id,
            "rank": g.rank if g else "not played",
            "words": len(found), "total_words": len(puzzle.answers),
            "pangrams": len(found & set(puzzle.pangrams)), "total_pangrams": len(puzzle.pangrams),
        })

    def table(data):
        t = Table(title=f"Spelling Bee {first} to {last}", title_justify="left", header_style="bold")
        for column in ("Date", "Rank", "Words", "Pangrams"):
            t.add_column(column)
        for row in data:
            t.add_row(row["date"], Text(row["rank"], style="bold yellow" if row["rank"] == "Queen Bee" else ""),
                      f"{row['words']}/{row['total_words']}", f"{row['pangrams']}/{row['total_pangrams']}")
        yield t

    emit(rows, fmt, table)
