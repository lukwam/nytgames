"""Render every nytg command in the table format, with made-up data.

The other CLI tests mostly check JSON output; these make sure the Rich tables,
grids and charts render without errors and show the key values.
"""
import datetime
from unittest import mock

import pytest
from typer.testing import CliRunner

from nytgames.cli import app as cli_app
from nytgames.cli import dates
from nytgames.cli import output
from nytgames.cli.state import State
from nytgames.models import ArchivePuzzle
from nytgames.models import ConnectionsPuzzle
from nytgames.models import CrosswordGame
from nytgames.models import CrosswordPuzzlesList
from nytgames.models import LetterBoxedPuzzle
from nytgames.models import Player
from nytgames.models import SpellingBeeGameDay
from nytgames.models import SpellingBeeLatest
from nytgames.models import StrandsPuzzle
from nytgames.models import WordlePuzzle
from nytgames.models import WordlePuzzlesList
from tests.test_formats import puzzle as crossword_puzzle

runner = CliRunner()
TODAY = "2026-10-04"

WORDLE = WordlePuzzle(id=1, days_since_launch=1933, editor="Ed", print_date=TODAY, solution="shack")
CONNECTIONS = ConnectionsPuzzle(id=1, status="OK", print_date=TODAY, editor="Ed", categories=[
    {"title": f"GROUP {g}", "cards": [{"content": f"WORD{g}{i}", "position": g * 4 + i} for i in range(4)]}
    for g in range(4)
])
STRANDS = StrandsPuzzle(
    id=1, clue="Gone fishing", editor="Ed", printDate=TODAY, solutions=["HOOK", "LINE"],
    spangram="BAIT", startingBoard=["HOOK", "LINE", "BAIT"],
    themeCoords={"HOOK": [[0, 0], [0, 1], [0, 2], [0, 3]], "LINE": [[1, 0], [1, 1], [1, 2], [1, 3]]},
    spangramCoords=[[2, 0], [2, 1], [2, 2], [2, 3]], themeWords=["HOOK", "LINE"],
)
BEE = SpellingBeeGameDay(
    id=1, answers=["blanchi", "chin", "hail"], centerLetter="i", displayDate="October 4, 2026",
    displayWeekday="Sunday", editor="Ed", outerLetters=list("abchln"), pangrams=["blanchi"],
    printDate=TODAY, validLetters=list("iabchln"),
)
LETTER_BOXED = LetterBoxedPuzzle(id=1, dictionary=["WHEREWITHAL", "LUMPY"], editor="Ed",
                                 ourSolution=["WHEREWITHAL", "LUMPY"], par=4, printDate=TODAY,
                                 sides=["LHY", "MIE", "RUT", "WAP"])
STATS = Player(user_id=1, stats={
    "wordle": {
        "totalStats": {"gamesPlayed": 10, "gamesWon": 9,
                       "guesses": {"1": 0, "2": 1, "3": 3, "4": 4, "5": 1, "6": 0, "fail": 1}},
        "calculatedStats": {"currentStreak": 3, "maxStreak": 7, "lastWonPrintDate": TODAY},
    },
    "connections": {"current_streak": 2, "max_streak": 5, "mistakes": {"0": 6, "1": 2, "4": 1},
                    "puzzles_completed": 9, "puzzles_won": 8},
    "strands": {"current_streak": 1, "max_streak": 4, "no_hints": 5, "puzzles_completed": 6,
                "puzzles_started": 7, "spangram_first": 3},
    "spelling_bee": {"puzzles_started": 5, "total_words": 200, "total_pangrams": 6,
                     "longest_word": {"word": "nationalization", "center_letter": "a", "print_date": TODAY},
                     "ranks": {"Genius": 2, "Queen Bee": 3}},
    "crossword_daily": {
        "puzzlesStarted": 8, "puzzlesSolved": 7, "solveRate": 0.875,
        "dailyStreaks": {"current": 4, "longest": 9},
        "dailyStats": {day: {"avgTimeSeconds": 600 + i * 300, "totalSolveTime": 6000, "totalSolves": 10,
                             "best": {"timeSeconds": 300, "date": "2026-01-05"}, "thisWeeksTime": 0,
                             "verticalStreak": {"current": 2, "longest": 3}}
                       for i, day in enumerate(dates.WEEKDAYS)},
    },
    "crossword_mini": {"avgTimeSeconds": 50, "bestDate": TODAY, "bestTimeSeconds": 14, "puzzlesSolved": 9,
                       "puzzlesStarted": 10, "solveRate": 0.9, "streaks": {"current": 3, "longest": 8}},
})
CROSSWORD_STATE = {"game": "crossword_daily", "print_date": TODAY, "puzzle_id": "1", "timestamp": 0,
                   "user_id": 1, "game_data": {"cells": {}, "firstSolve": 1, "completionFraction": 1,
                                               "playTimeSeconds": 754, "star": "gold"}}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NYTG_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.setattr(dates, "today", lambda: datetime.date(2026, 10, 4))
    output.default_format = None


@pytest.fixture
def client(monkeypatch):
    fake = mock.Mock()
    fake.wordle.return_value = WORDLE
    fake.connections.return_value = CONNECTIONS
    fake.strands.return_value = STRANDS
    fake.spelling_bee_puzzle.return_value = BEE
    fake.letter_boxed.return_value = LETTER_BOXED
    fake.crossword.return_value = crossword_puzzle()
    fake.player_stats.return_value = STATS
    fake.wordle_latest.return_value = WordlePuzzlesList(user_id=1, states=[{
        "game": "wordleV2", "print_date": TODAY, "puzzle_id": "1", "timestamp": 0, "user_id": 1,
        "game_data": {"boardState": ["adieu", "shack", "", "", "", ""], "currentRowIndex": 2,
                      "status": "WIN"}}])
    fake.spelling_bee_latest.return_value = SpellingBeeLatest(user_id=1, states=[{
        "game": "spelling_bee", "print_date": TODAY, "puzzle_id": "1", "schema_version": "1",
        "timestamp": 0, "user_id": 1, "version": "1",
        "game_data": {"answers": ["chin", "blanchi"], "isRevealed": False, "rank": "Genius"}}],
        player={"user_id": 1})
    fake.crossword_puzzles.return_value = CrosswordPuzzlesList(status="OK", results=[{
        "author": "Ann Author", "editor": "Ed", "format_type": "Normal", "percent_filled": 100,
        "print_date": TODAY, "publish_type": "Daily", "puzzle_id": 1, "solved": True, "star": "Gold",
        "title": "", "version": 0}])
    fake.crossword_game.return_value = CrosswordGame(user_id=1, states=[CROSSWORD_STATE])
    fake.archive.return_value = [ArchivePuzzle(id=1, print_date=TODAY, byline="Ann Author")]
    monkeypatch.setattr(State, "client", lambda self: fake)
    return fake


def table(*args: str) -> str:
    result = runner.invoke(cli_app.app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


@pytest.mark.parametrize("args,expected", [
    (["wordle"], ["Wordle 1933"]),
    (["wordle", "--answers"], ["S", "H", "A", "C", "K"]),
    (["connections"], ["WORD00", "WORD33"]),
    (["connections", "--answers"], ["GROUP 0", "WORD32, WORD33"]),
    (["strands"], ["Gone fishing", "H  O  O  K"]),
    (["strands", "--answers"], ["Spangram: BAIT", "HOOK, LINE"]),
    (["bee", "--hints"], ["3 words", "Two letter list", "BL-1"]),
    (["bee", "--answers"], ["blanchi", "chin", "hail"]),
    (["letter-boxed", "--answers"], ["solve in 4 words", "WHEREWITHAL → LUMPY"]),
    (["crossword", "mini"], ["Mini crossword 2025-06-12", "Across", "First “row”"]),
    (["crossword", "daily", "--answers"], ["HH", "Right – column"]),
])
def test_puzzle_tables(client, args, expected):
    rendered = table(*args)
    for text in expected:
        assert text in rendered
    if "--answers" not in args and args[0] == "wordle":
        assert "SHACK" not in rendered.upper().replace(" ", "")


@pytest.mark.parametrize("game,expected", [
    ("all", ["Wordle", "Connections", "Crossword", "90"]),
    ("wordle", ["Guess distribution", "fail"]),
    ("connections", ["Mistakes", "Won"]),
    ("strands", ["Spangram first"]),
    ("bee", ["Best rank reached", "Queen Bee", "nationalization"]),
    ("crossword", ["Monday", "Sunday", "10:00", "Mini"]),
])
def test_stats_tables(client, game, expected):
    rendered = table("stats", game)
    for text in expected:
        assert text in rendered


def test_today_table(client):
    rendered = table("today")
    for text in ("Today's games (2026-10-04)", "Wordle", "Spelling Bee", "Genius", "Crossword", "12:34"):
        assert text in rendered


@pytest.mark.parametrize("args,expected", [
    (["history", "crossword"], ["Daily crosswords", "Ann Author", "12:34", "1 solved"]),
    (["history", "crossword", "midi"], ["Midi crosswords", "Ann Author"]),
    (["history", "wordle"], ["ADIEU SHACK", "win"]),
    (["history", "bee"], ["Genius", "2/3", "1/1"]),
])
def test_history_tables(client, args, expected):
    rendered = table(*args)
    for text in expected:
        assert text in rendered


def test_config_and_auth_tables(client):
    assert "Profile" in table("config", "profiles", "list")
    runner.invoke(cli_app.app, ["config", "set", "cookies", "NYT-S=secretvalue123"])
    listed = table("config", "list")
    assert "NYT-S=secret…" in listed and "secretvalue123" not in listed
    rendered = table("auth", "status")
    assert "logged in" in rendered and "1" in rendered
