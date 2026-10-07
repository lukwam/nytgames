"""Plain data views of puzzles and results, shared by nytg and the MCP server.

Each view returns JSON-compatible data. Puzzle views hide answers unless
`answers` is true.
"""
import datetime
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from typing import Any

from nytgames import spelling_bee_hints
from nytgames.exceptions import NYTGamesNotFoundError

# NYT returns game states for at most 30 puzzle IDs per request.
STATE_BATCH = 30
# NYT's crossword list returns at most 100 puzzles per request.
LIST_DAYS = 90

TITLES = {"daily": "New York Times Crossword", "mini": "NYT Mini Crossword",
          "midi": "NYT Midi Crossword", "bonus": "NYT Bonus Crossword"}

Progress = Callable[[Iterable, int, str], Iterable]


def no_progress(items: Iterable, total: int, description: str) -> Iterable:
    return items


def chunks(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def percent(part: int | None, whole: int | None) -> float | None:
    return round(100 * part / whole, 1) if part is not None and whole else None


def format_seconds(seconds: int | None) -> str:
    """Format a duration as M:SS or H:MM:SS."""
    if seconds is None:
        return ""
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02}:{secs:02}" if hours else f"{minutes}:{secs:02}"


def date_range(start: datetime.date, end: datetime.date) -> Iterator[datetime.date]:
    for offset in range((end - start).days + 1):
        yield start + datetime.timedelta(days=offset)


# Puzzles


def wordle_view(puzzle, answers: bool = False) -> dict:
    data = {"date": puzzle.print_date, "number": puzzle.days_since_launch, "id": puzzle.id,
            "editor": puzzle.editor}
    if answers:
        data["solution"] = puzzle.solution
    return data


def connections_view(puzzle, answers: bool = False) -> dict:
    words = [card.text for row in puzzle.board() for card in row]
    data = {"date": puzzle.print_date, "id": puzzle.id, "editor": puzzle.editor,
            "board": [words[i:i + 4] for i in range(0, len(words), 4)]}
    if answers:
        data["categories"] = [{"title": category.title, "cards": [card.text for card in category.cards]}
                              for category in puzzle.categories]
    return data


def strands_view(puzzle, answers: bool = False) -> dict:
    data = {"date": puzzle.printDate, "id": puzzle.id, "clue": puzzle.clue, "editor": puzzle.editor,
            "board": puzzle.startingBoard}
    if answers:
        data["spangram"] = puzzle.spangram
        data["theme_words"] = puzzle.themeWords or list(puzzle.themeCoords)
        data["spangram_coords"] = puzzle.spangramCoords or []
        data["theme_coords"] = puzzle.themeCoords
    return data


def bee_view(puzzle, answers: bool = False, hints: bool = False) -> dict:
    puzzle_hints = spelling_bee_hints(puzzle)
    data = {"date": puzzle.printDate, "id": puzzle.id, "editor": puzzle.editor,
            "center_letter": puzzle.centerLetter, "outer_letters": puzzle.outerLetters,
            "words": puzzle_hints["words"], "points": puzzle_hints["points"],
            "pangrams": puzzle_hints["pangrams"]}
    if hints:
        data["hints"] = puzzle_hints
    if answers:
        data["answers"] = puzzle.answers
        data["pangram_words"] = puzzle.pangrams
    return data


def letter_boxed_view(puzzle, answers: bool = False) -> dict:
    data = {"date": puzzle.printDate, "id": puzzle.id, "editor": puzzle.editor, "sides": puzzle.sides,
            "par": puzzle.par}
    if answers:
        data["solution"] = puzzle.ourSolution
        data["dictionary"] = puzzle.dictionary
    return data


def crossword_view(puzzle, kind: str, answers: bool = False, clues: bool = True,
                   entries: bool = False) -> dict:
    """A crossword's grid and clues; `entries` adds each entry's position and crossings."""
    body = puzzle.body[0]
    width = body.dimensions["width"]
    cells = body.cells

    def cell_text(cell):
        if not cell.type:
            return "#"
        return (cell.answer or "") if answers else "."

    grid = ["".join(cell_text(c)[:1] or "." for c in cells[r * width:(r + 1) * width])
            for r in range(len(cells) // width)]
    data = {
        "date": puzzle.publicationDate,
        "type": kind,
        "id": puzzle.id,
        "title": puzzle.title,
        "constructors": puzzle.constructors,
        "editor": puzzle.editor,
        "size": f"{width}x{len(grid)}",
        "grid": grid,
    }
    if clues:
        clue_lists = {}
        for clue_list in body.clueLists:
            items = []
            for index in clue_list.clues:
                clue = body.clues[index]
                item = {"label": clue.label, "clue": "".join(t.get("plain", "") for t in clue.text)}
                if answers:
                    # Some clues that turn corners repeat the corner square.
                    squares = [i for n, i in enumerate(clue.cells) if n == 0 or i != clue.cells[n - 1]]
                    item["answer"] = "".join(cells[i].answer or "" for i in squares)
                items.append(item)
            clue_lists[clue_list.name.lower()] = items
        data["clues"] = clue_lists
    if entries:
        data["entries"] = []
        for entry in puzzle.entries():
            item = {"id": entry.id, "direction": entry.direction, "clue": entry.clue,
                    "length": entry.length, "start": list(entry.coordinates[0]),
                    "crossings": list(entry.crossings)}
            if entry.references:
                item["references"] = list(entry.references)
            if answers:
                item["answer"] = entry.answer
            data["entries"].append(item)
    notes = " ".join(n.get("text", "") for n in (puzzle.notes or []) if isinstance(n, dict)).strip()
    if notes:
        data["notes"] = notes
    return data


def export_title(puzzle, kind: str) -> str:
    """The title for an exported crossword file."""
    date = datetime.date.fromisoformat(puzzle.publicationDate)
    title = f"{TITLES[kind]}, {date:%B} {date.day}, {date.year}"
    return f"{title}: {puzzle.title}" if puzzle.title else title


# Your results


def wordle_status(game) -> str:
    """A Wordle game's status, such as "win", for either saved game format."""
    if game.status:
        return game.status.lower().replace("_", " ")
    return "played" if game.puzzleComplete else "in progress"


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


def crossword_results(client, kind: str, first: datetime.date, last: datetime.date,
                      progress: Progress = no_progress) -> list[dict]:
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


def wordle_results(client, first: datetime.date, last: datetime.date) -> list[dict]:
    """Return the user's Wordle results for a date range."""
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
            "status": wordle_status(g) if g else "not played",
            "guesses": g.currentRowIndex if g and g.status == "WIN" else None,
            "hard_mode": g.hardMode if g else None,
            "board": [w for w in g.boardState if w] if g else [],
        })
    return rows


def connections_status(game) -> str:
    """A Connections game's status: won, lost or in progress."""
    if game.puzzleWon:
        return "won"
    return "lost" if game.puzzleComplete else "in progress"


def connections_results(client, first: datetime.date, last: datetime.date) -> list[dict]:
    """Return the user's Connections results for a date range."""
    ids = {p.id: p.print_date for p in client.archive("connections", first.isoformat(), last.isoformat())}
    states = {}
    for batch in chunks(list(ids), STATE_BATCH):
        for game in client.connections_latest(batch).states:
            states[int(game.puzzle_id)] = game.game_data
    rows = []
    for puzzle_id, day in ids.items():
        g = states.get(puzzle_id)
        rows.append({
            "date": day, "puzzle_id": puzzle_id,
            "status": connections_status(g) if g else "not played",
            "mistakes": g.mistakes if g else None,
            "categories_solved": len(g.solvedCategories) if g else 0,
            "archive": g.isPlayingArchive if g else None,
        })
    return rows


def strands_results(client, first: datetime.date, last: datetime.date) -> list[dict]:
    """Return the user's Strands results for a date range."""
    ids = {p.id: p.print_date for p in client.archive("strands", first.isoformat(), last.isoformat())}
    states = {}
    for batch in chunks(list(ids), STATE_BATCH):
        for game in client.strands_latest(batch).states:
            states[int(game.puzzle_id)] = game.game_data
    rows = []
    for puzzle_id, day in ids.items():
        g = states.get(puzzle_id)
        rows.append({
            "date": day, "puzzle_id": puzzle_id,
            "status": ("solved" if g.isSolved else "in progress") if g else "not played",
            "other_words": len(g.otherWordsFound) if g else 0,
            "archive": g.isPlayingArchive if g else None,
        })
    return rows


def bee_results(client, first: datetime.date, last: datetime.date,
                progress: Progress = no_progress) -> list[dict]:
    """Return the user's Spelling Bee results for a date range."""
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
            "rank": (g.rank or "played") if g else "not played",
            "words": len(found), "total_words": len(puzzle.answers),
            "pangrams": len(found & set(puzzle.pangrams)), "total_pangrams": len(puzzle.pangrams),
        })
    return rows


def today_rows(client, day: datetime.date) -> list[dict]:
    """Return which of a day's games the user has played."""
    iso = day.isoformat()
    player = client.player_stats()
    rows = []

    states = client.wordle_latest(client.wordle(iso).id).states
    if states:
        g = states[0].game_data
        rows.append({"game": "Wordle", "status": wordle_status(g),
                     "detail": f"{g.currentRowIndex}/6" if g.status == "WIN" else ""})
    else:
        rows.append({"game": "Wordle", "status": "not played", "detail": ""})

    for name, s in (("Connections", player.stats.connections), ("Strands", player.stats.strands)):
        played = bool(s and s.last_played_print_date == iso)
        rows.append({"game": name, "status": "played" if played else "not played", "detail": ""})

    bee = client.spelling_bee_puzzle(iso)
    states = client.spelling_bee_latest(bee.id).states
    if states:
        g = states[0].game_data
        rows.append({"game": "Spelling Bee", "status": g.rank or "played",
                     "detail": f"{len(g.answers)}/{len(bee.answers)} words"})
    else:
        rows.append({"game": "Spelling Bee", "status": "not played", "detail": ""})

    for kind in ("daily", "mini", "midi"):
        results = crossword_results(client, kind, day, day)
        if not results:
            continue
        r = results[0]
        status = ("solved" if r["solved"] else "in progress" if r["percent_filled"] else "not played")
        detail = " ".join(x for x in (format_seconds(r["seconds"]) if r["seconds"] else "",
                                      "⭐" if (r["star"] or "").lower() == "gold" else "") if x)
        rows.append({"game": "Crossword" if kind == "daily" else kind.title(), "status": status,
                     "detail": detail})
    return rows


# Badges

BADGE_GAME_NAMES = {"wordleV2": "Wordle", "connections": "Connections", "strands": "Strands",
                    "spelling_bee": "Spelling Bee"}


def badge_view(badge) -> dict:
    """Return a badge with its name, description and artwork at your level,
    or at the next level if you haven't earned it."""
    info = badge.info
    level = badge.level if badge.is_earned else badge.next_level
    earned_at = max(badge.earned_at, default=None)
    return {
        "id": badge.id,
        "name": info.name(level) if info else badge.id,
        "type": badge.badge_type,
        "earned": badge.is_earned,
        "level": badge.level,
        "next_level": badge.next_level,
        "progress": badge.progress,
        "last_earned": (datetime.datetime.fromtimestamp(earned_at, datetime.timezone.utc).date().isoformat()
                        if earned_at else None),
        "description": info.description(level, badge.is_earned, badge.progress) if info else None,
        "image_url": info.image_url(level, badge.is_earned) if info else None,
    }


def badge_rows(case) -> list[dict]:
    """Return every badge in a trophy case, earned ones first, by game."""
    return [{"game": BADGE_GAME_NAMES.get(game, game), **badge_view(badge)}
            for game, trophies in case.trophies.items() for badge in trophies.badges]


# WordleBot


def skill_rank(efficiency: float | None, percentiles: dict | None) -> list | None:
    """Return the [low, high] percentiles a skill score falls between.

    NYT publishes only some percentiles (e.g. p25 and p75 but nothing between),
    so this is a range. 0 means below the lowest published percentile and
    100 above the highest.
    """
    if efficiency is None or not percentiles:
        return None
    points = sorted((int(key[1:]), value) for key, value in percentiles.items() if key[1:].isdigit())
    low = max((p for p, value in points if efficiency >= value), default=0)
    high = min((p for p, value in points if efficiency < value), default=100)
    return [low, high]


def describe_rank(rank: list) -> str:
    low, high = rank
    if high == 100:
        return f"your skill was above the {low}th percentile"
    if low == 0:
        return f"your skill was below the {high}th percentile"
    return f"your skill was between the {low}th and {high}th percentiles"


def wordlebot_view(day: datetime.date, puzzle, summary, mine=None, answers: bool = False) -> dict:
    """Compare the user's WordleBot analysis (if any) with everyone's."""
    if mine is not None and mine.gameNumber != puzzle.days_since_launch:
        mine = None
    mode = mine.mode if mine and mine.mode in ("normal", "hard") else "normal"

    def by_mode(values):
        return (values or {}).get(mode)

    data = {
        "date": day.isoformat(),
        "number": puzzle.days_since_launch,
        "mode": mode,
        "everyone": {
            "players": (summary.steps or {}).get(f"{mode}Users"),
            "average_guesses": by_mode(summary.average),
            "skill": by_mode(summary.efficiency),
            "luck": by_mode(summary.luck),
            "solved_in_three_or_fewer": by_mode(summary.percentSolvingInThreeOrFewer),
        },
    }
    if mine is not None:
        data["you"] = {
            "guesses": mine.guess_list,
            "skill": mine.efficiency,
            "luck": mine.luck,
            "skill_percentile_range": skill_rank(mine.efficiency, by_mode(summary.percentiles)),
            "skill_by_round": mine.efficiencyByRound,
            "luck_by_round": mine.luckByRound,
        }
    if answers:
        data["bot_paths"] = summary.guesses or {}
    return data
