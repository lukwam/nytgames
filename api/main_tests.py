"""NYT Games API tests.

These tests mock the upstream NYT requests, so they run offline and do not
need NYT cookies.
"""
from unittest import mock

import pytest
import requests
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def mock_response(json_data=None, status_code=200, content=b""):
    """Return a mock requests.Response."""
    response = mock.Mock(spec=requests.Response)
    response.status_code = status_code
    response.content = content
    response.json.return_value = json_data
    response.request = mock.Mock(url="https://www.nytimes.com/mock")
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    else:
        response.raise_for_status.return_value = None
    return response


@pytest.fixture
def nyt():
    """Patch requests.get in main and yield the mock."""
    with mock.patch("main.requests.get") as patched:
        yield patched


WORDLE = {
    "id": 1,
    "solution": "cigar",
    "print_date": "2021-06-19",
}

CROSSWORD_DAILY = {
    "id": 1,
    "constructors": ["A. Constructor"],
    "copyright": "2025",
    "editor": "Will Shortz",
    "lastUpdated": "2025-06-12 00:00:00 +0000 UTC",
    "publicationDate": "2025-06-12",
    "relatedContent": {"text": "", "url": ""},
    "body": [{
        "board": "<svg></svg>",
        "cells": [
            {"answer": "A", "clues": [0], "label": 1, "type": 1},
            {"answer": "LL", "clues": [0], "moreAnswers": {"valid": ["L"]}, "type": 1},
            {},
        ],
        "clues": [{
            "cells": [0, 1],
            "direction": "Across",
            "label": "1",
            "text": [{"plain": "Clue"}],
        }],
        "clueLists": [{"clues": [0], "name": "Across"}],
        "dimensions": {"height": 1, "width": 3},
        "SVG": {},
    }],
}

STATE_LATESTS = {
    "user_id": 123,
    "states": [],
    "player": {
        "user_id": 123,
        "last_updated": 0,
        "stats": {
            "spelling_bee": {
                "puzzles_started": 1,
                "total_words": 2,
                "total_pangrams": 0,
                "longest_word": {"word": "abcd", "center_letter": "a", "print_date": "2025-06-12"},
                "ranks": {
                    "Amazing": 0, "Beginner": 0, "Genius": 0, "Good": 0, "Good Start": 0,
                    "Great": 0, "Moving Up": 0, "Nice": 0, "Queen Bee": 0, "Solid": 0,
                },
            },
            "wordle": {"legacyStats": {
                "autoOptInTimestamp": 0, "currentStreak": 0, "gamesPlayed": 0, "gamesWon": 0,
                "guesses": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "fail": 0},
                "hasMadeStatsChoice": False, "hasPlayed": False, "lastWonDayOffset": 0,
                "maxStreak": 0, "timestamp": 0,
            }},
        },
    },
    "badges_trophy_shelf": [],
    "crossword_archive_streaks": {"vertical": None, "horizontal": None},
}


def test_wordle_early_puzzle_without_optional_fields(nyt):
    """Early Wordle puzzles have no days_since_launch or editor."""
    nyt.return_value = mock_response(WORDLE)
    response = client.get("/wordle/2021-06-19")
    assert response.status_code == 200
    assert response.json()["solution"] == "cigar"


def test_unknown_fields_are_passed_through(nyt):
    """New NYT fields do not break validation and appear in the response."""
    nyt.return_value = mock_response({**WORDLE, "new_field": "value"})
    response = client.get("/wordle/2021-06-19")
    assert response.status_code == 200
    assert response.json()["new_field"] == "value"


def test_crossword_daily_uses_v6_endpoint(nyt):
    """Daily crosswords use the v6 format, including rebus cells."""
    nyt.return_value = mock_response(CROSSWORD_DAILY)
    response = client.get("/crosswords/daily/2025-06-12")
    assert response.status_code == 200
    cell = response.json()["body"][0]["cells"][1]
    assert cell["answer"] == "LL"
    assert cell["moreAnswers"] == {"valid": ["L"]}
    assert nyt.call_args.args[0] == (
        "https://www.nytimes.com/svc/crosswords/v6/puzzle/daily/2025-06-12.json"
    )


@pytest.mark.parametrize("path", ["/spelling-bee/latest", "/wordle/latest"])
def test_state_latests(nyt, path):
    """Game state endpoints accept the current response shape."""
    nyt.return_value = mock_response(STATE_LATESTS)
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["user_id"] == 123


def test_strands_uses_v2_endpoint(nyt):
    """Strands is fetched from the svc/strands/v2 endpoint."""
    nyt.return_value = mock_response({
        "id": 1,
        "clue": "Clue",
        "editor": "Editor",
        "printDate": "2025-06-12",
        "solutions": ["WORD"],
        "spangram": "SPANGRAM",
        "startingBoard": ["ABCDEF"],
        "themeCoords": {"WORD": [[0, 0]]},
    })
    response = client.get("/strands/2025-06-12")
    assert response.status_code == 200
    assert nyt.call_args.args[0] == "https://www.nytimes.com/svc/strands/v2/2025-06-12.json"


def test_upstream_error_status_is_passed_through(nyt):
    """Upstream NYT errors return the upstream status code, not a 500."""
    nyt.return_value = mock_response(status_code=404)
    response = client.get("/wordle/1900-01-01")
    assert response.status_code == 404
    assert response.json()["detail"] == "NYT API returned 404"


def test_get_game_data():
    """Spelling Bee game data is parsed from the page script tag."""
    body = b'<html><script>window.gameData = {"today": {"id": 1}}</script></html>'
    assert main.get_game_data(body) == {"today": {"id": 1}}
    assert main.get_game_data(b"<html></html>") is None


def test_crossword_game_uses_game_state_endpoint(nyt):
    """Crossword game state is fetched from the games state service."""
    nyt.return_value = mock_response({
        "user_id": 123,
        "player": {},
        "states": [{
            "game": "crossword_mini",
            "game_data": {"cells": {}, "playTimeSeconds": 30, "star": "blue"},
            "print_date": "2026-07-17",
            "puzzle_id": "24291",
            "timestamp": 0,
            "user_id": 123,
        }],
        "crossword_archive_streaks": {"vertical": None, "horizontal": None},
    })
    response = client.get("/crosswords/game/24291?publish_type=mini")
    assert response.status_code == 200
    assert response.json()["states"][0]["game_data"]["playTimeSeconds"] == 30
    assert nyt.call_args.args[0] == (
        "https://www.nytimes.com/svc/games/state/crossword_mini/latests"
    )
    assert nyt.call_args.kwargs["params"] == {"puzzle_ids": "24291"}


def test_crossword_oracle(nyt):
    """The oracle returns the current and next puzzle."""
    puzzle = {"puzzle_id": 1, "print_date": "2026-10-04", "published": "2026-10-03 18:00:00", "time_delta": 0}
    nyt.return_value = mock_response({"status": "OK", "results": {"current": puzzle, "next": puzzle}})
    response = client.get("/crosswords/oracle/midi")
    assert response.status_code == 200
    assert response.json()["results"]["current"]["puzzle_id"] == 1
    assert nyt.call_args.args[0] == "https://www.nytimes.com/svc/crosswords/v2/oracle/midi.json"


def test_crossword_oracle_rejects_unknown_type():
    """Unknown publish types are rejected before calling NYT."""
    assert client.get("/crosswords/oracle/nope").status_code == 422
