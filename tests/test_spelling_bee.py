"""Spelling Bee puzzles and hints tests.

The hints cases are ported from nyt-puzzles so both stay in agreement.
"""
import json
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import main
from nytgames import NYTGamesClient
from nytgames import spelling_bee_hints
from nytgames.models import SpellingBeeGameDay


def make_puzzle(print_date, answers, letters="iabchln", pangrams=None):
    """Build a puzzle shaped like the ones on the public Spelling Bee page."""
    return {
        "answers": answers,
        "centerLetter": letters[0],
        "displayDate": print_date,
        "displayWeekday": "Saturday",
        "editor": "Sam Ezersky",
        "freeExpiration": 0,
        "id": 1,
        "outerLetters": list(letters[1:]),
        "pangrams": pangrams or [],
        "printDate": print_date,
        "validLetters": list(letters),
    }


def make_page(puzzles):
    """Build Spelling Bee page HTML embedding the given puzzles, newest first."""
    game_data = {
        "today": puzzles[0],
        "yesterday": puzzles[1],
        "pastPuzzles": {
            "today": puzzles[0],
            "yesterday": puzzles[1],
            "thisWeek": puzzles[2:3],
            "lastWeek": puzzles[3:],
        },
    }
    return f"<html><script>window.gameData = {json.dumps(game_data)}</script></html>".encode()


PUZZLES = [
    make_puzzle("2026-10-03", ["bacchanalia", "chin", "hail"], pangrams=["bacchanalia"]),
    make_puzzle("2026-10-02", ["tilt"], letters="tilxyzw"),
    make_puzzle("2026-10-01", ["tilt"], letters="tilxyzw"),
    make_puzzle("2026-09-21", ["tilt"], letters="tilxyzw"),
]


@pytest.fixture
def page():
    """Patch the HTTP session to return a Spelling Bee page."""
    with mock.patch("requests.Session.get") as patched:
        response = patched.return_value
        response.status_code = 200
        response.content = make_page(PUZZLES)
        response.raise_for_status.return_value = None
        yield patched


def test_hints_counts_words_by_first_letter_and_length():
    puzzle = make_puzzle("2026-10-03", ["chin", "hail", "laicb", "bacchanalia"])

    hints = spelling_bee_hints(puzzle)

    assert hints["counts"] == {
        "lengths": [4, 5, 11],
        "letters": {"b": [0, 0, 1, 1], "c": [1, 0, 0, 1], "h": [1, 0, 0, 1], "l": [0, 1, 0, 1]},
        "totals": [2, 1, 1, 4],
    }
    assert hints["pairs"] == {"ba": 1, "ch": 1, "ha": 1, "la": 1}
    assert hints["letters"] == ["i", "a", "b", "c", "h", "l", "n"]
    assert hints["date"] == "2026-10-03"
    assert hints["words"] == 4


def test_hints_score_pangrams_with_bonus():
    # 4-letter words score 1; longer words score their length, plus 7 for a pangram.
    puzzle = make_puzzle("2026-10-03", ["chin", "hail", "bacchanalia"])

    hints = spelling_bee_hints(puzzle)

    assert hints["pangrams"] == 1
    assert hints["points"] == 1 + 1 + 11 + 7
    assert "perfect" not in hints


def test_hints_count_perfect_pangrams():
    puzzle = make_puzzle("2026-10-03", ["blanchi", "chin"])

    assert spelling_bee_hints(puzzle)["perfect"] == 1


def test_hints_mark_bingo_only_when_every_letter_starts_a_word():
    answers = ["inch", "abba", "bail", "chai", "hail", "lain", "nail"]

    assert spelling_bee_hints(make_puzzle("d", answers))["bingo"] is True
    assert "bingo" not in spelling_bee_hints(make_puzzle("d", answers[1:]))


def test_hints_lowercase_answers():
    hints = spelling_bee_hints(make_puzzle("d", ["CHIN"]))

    assert hints["pairs"] == {"ch": 1}


def test_hints_accept_a_model():
    puzzle = make_puzzle("2026-10-03", ["chin", "hail", "bacchanalia"])

    assert spelling_bee_hints(SpellingBeeGameDay(**puzzle)) == spelling_bee_hints(puzzle)


def test_spelling_bee_puzzles_reads_every_puzzle_on_the_page(page):
    puzzles = NYTGamesClient().spelling_bee_puzzles()

    assert list(puzzles) == ["2026-09-21", "2026-10-01", "2026-10-02", "2026-10-03"]
    assert puzzles["2026-10-03"].answers == PUZZLES[0]["answers"]


def test_spelling_bee_fails_without_game_data(page):
    page.return_value.content = b"<html></html>"

    with pytest.raises(ValueError, match="game data not found"):
        NYTGamesClient().spelling_bee_puzzles()


def test_api_date_route_returns_404_outside_the_page(page):
    client = TestClient(main.app)

    assert client.get("/spelling-bee/2026-10-02").status_code == 200
    assert client.get("/spelling-bee/2020-01-01").status_code == 404


def test_api_hints_route(page):
    response = TestClient(main.app).get("/spelling-bee/2026-10-03/hints")

    assert response.status_code == 200
    assert response.json() == spelling_bee_hints(PUZZLES[0])


def test_api_latest_route_is_not_treated_as_a_date(page):
    TestClient(main.app, raise_server_exceptions=False).get("/spelling-bee/latest")

    assert page.call_args.args[0].endswith("/svc/games/state/spelling_bee/latests")
