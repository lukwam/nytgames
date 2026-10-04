"""NYT Games client tests.

These tests mock the HTTP session, so they run offline and do not need NYT
cookies.
"""
from unittest import mock

import pytest
import requests

from nytgames import NYTGamesClient
from nytgames import parse_cookies


@pytest.fixture
def session():
    """Return a mock requests.Session."""
    session = mock.Mock(spec=requests.Session)
    response = session.get.return_value
    response.status_code = 200
    response.raise_for_status.return_value = None
    return session


@pytest.mark.parametrize("cookies", [
    {"NYT-S": "abc", "nyt-a": "def"},
    [{"name": "NYT-S", "value": "abc", "domain": ".nytimes.com"}, {"name": "nyt-a", "value": "def"}],
    "NYT-S=abc; nyt-a=def",
])
def test_parse_cookies(cookies):
    """Cookies can be a dict, a Cookie-Editor JSON export or a header string."""
    assert parse_cookies(cookies) == {"NYT-S": "abc", "nyt-a": "def"}


def test_parse_cookies_empty():
    """No cookies is an empty dict."""
    assert parse_cookies(None) == {}


def test_cookies_are_sent(session):
    """Cookies are sent with every request."""
    session.get.return_value.json.return_value = {"id": 1, "solution": "cigar", "print_date": "2021-06-19"}
    client = NYTGamesClient(cookies="NYT-S=abc", session=session)
    puzzle = client.wordle("2021-06-19")
    assert puzzle.solution == "cigar"
    assert session.get.call_args.kwargs["cookies"] == {"NYT-S": "abc"}


@pytest.mark.parametrize("publish_type,date,path", [
    ("daily", None, "/svc/crosswords/v6/puzzle/daily.json"),
    ("daily", "2025-06-12", "/svc/crosswords/v6/puzzle/daily/2025-06-12.json"),
    ("mini", "2025-06-12", "/svc/crosswords/v6/puzzle/mini/2025-06-12.json"),
    ("midi", None, "/svc/crosswords/v6/puzzle/midi.json"),
    ("bonus", "1997-02-01", "/svc/crosswords/v6/puzzle/bonus/1997-02-01.json"),
])
def test_crossword_url(session, publish_type, date, path):
    """Crossword puzzles are fetched from the v6 endpoint for each type."""
    session.get.return_value.json.return_value = {
        "id": 1,
        "body": [],
        "constructors": [],
        "copyright": "",
        "lastUpdated": "",
        "publicationDate": "",
    }
    NYTGamesClient(session=session).crossword(publish_type, date)
    assert session.get.call_args.args[0] == f"https://www.nytimes.com{path}"


def test_crossword_rejects_unknown_type(session):
    """Unknown publish types raise ValueError before calling NYT."""
    with pytest.raises(ValueError):
        NYTGamesClient(session=session).crossword("weekly")
    session.get.assert_not_called()


def test_unset_params_are_not_sent(session):
    """Params that are not set are left out of the request."""
    session.get.return_value.json.return_value = {"results": [], "status": "OK"}
    NYTGamesClient(session=session).crossword_puzzles(publish_type="midi", date_start="2026-10-01")
    assert session.get.call_args.kwargs["params"] == {"publish_type": "midi", "date_start": "2026-10-01"}


def test_http_errors_are_raised(session):
    """HTTP errors from NYT are raised as requests.HTTPError."""
    session.get.return_value.raise_for_status.side_effect = requests.HTTPError("404")
    with pytest.raises(requests.HTTPError):
        NYTGamesClient(session=session).wordle("1900-01-01")


def test_letter_boxed(session):
    """Letter Boxed puzzles are fetched from the v1 endpoint by date."""
    session.get.return_value.json.return_value = {
        "id": 2860,
        "dictionary": ["LUMPY", "WHEREWITHAL"],
        "editor": "Sam Ezersky",
        "is_free": True,
        "ourSolution": ["WHEREWITHAL", "LUMPY"],
        "par": 4,
        "printDate": "2026-10-03",
        "sides": ["LHY", "MIE", "RUT", "WAP"],
    }
    puzzle = NYTGamesClient(session=session).letter_boxed("2026-10-03")
    assert puzzle.sides == ["LHY", "MIE", "RUT", "WAP"]
    assert puzzle.model_dump()["is_free"] is True
    assert session.get.call_args.args[0] == "https://www.nytimes.com/svc/letter-boxed/v1/2026-10-03.json"


@pytest.mark.parametrize("status,error", [
    (401, "NYTGamesAuthenticationError"),
    (403, "NYTGamesAuthenticationError"),
    (404, "NYTGamesNotFoundError"),
    (500, "NYTGamesHTTPError"),
])
def test_http_errors_are_typed(session, status, error):
    """HTTP errors are raised as NYTGames errors that are still requests.HTTPError."""
    import nytgames
    response = session.get.return_value
    response.status_code = status
    response.raise_for_status.side_effect = requests.HTTPError(str(status), response=response)
    with pytest.raises(getattr(nytgames, error)) as info:
        NYTGamesClient(session=session).wordle("2026-10-03")
    assert isinstance(info.value, requests.HTTPError)
    assert info.value.response.status_code == status


def test_user_agent_identifies_the_library(session):
    """Requests identify nytgames in the User-Agent."""
    import nytgames
    session.get.return_value.json.return_value = {"id": 1, "solution": "cigar", "print_date": "2021-06-19"}
    NYTGamesClient(session=session).wordle("2021-06-19")
    assert session.get.call_args.kwargs["headers"]["User-Agent"].startswith(f"nytimes-games/{nytgames.__version__}")


def test_player_stats(session):
    """Player stats are read from the game state service with puzzle_ids=0."""
    session.get.return_value.json.return_value = {
        "user_id": 123,
        "states": [],
        "player": {
            "user_id": 123,
            "stats": {
                "connections": {
                    "current_streak": 150, "max_streak": 302, "mistakes": {"0": 1},
                    "puzzles_completed": 850, "puzzles_won": 840,
                },
                "wordle": {
                    "legacyStats": {
                        "currentStreak": 72, "gamesPlayed": 1260, "gamesWon": 1228,
                        "guesses": {"1": 2, "2": 39, "3": 314, "4": 484, "5": 281, "6": 108, "fail": 32},
                        "maxStreak": 144,
                    },
                    "calculatedStats": {"currentStreak": 3, "maxStreak": 144},
                },
                "crossplay": {"won": 0},
            },
        },
    }
    player = NYTGamesClient(cookies="NYT-S=abc", session=session).player_stats()
    assert player.user_id == 123
    assert player.stats.connections.puzzles_won == 840
    assert player.stats.wordle.legacyStats.guesses.three == 314
    assert player.stats.wordle.calculatedStats.currentStreak == 3
    assert player.stats.strands is None
    assert player.stats.model_dump()["crossplay"] == {"won": 0}
    assert session.get.call_args.kwargs["params"] == {"puzzle_ids": "0"}


def test_old_stats_model_names_still_import():
    """Model names from v0.1.0 still work."""
    from nytgames.models import Player
    from nytgames.models import SpellingBeePlayer
    assert SpellingBeePlayer is Player


def test_connections_picture_puzzle(session):
    """Picture puzzle cards have image fields instead of content."""
    image_card = {
        "position": 4,
        "image_url": "https://games-phoenix-assets-prd.s3.us-east-1.amazonaws.com/slot-machine.svg",
        "image_alt_text": "SLOT MACHINE",
    }
    session.get.return_value.json.return_value = {
        "id": 1,
        "status": "OK",
        "print_date": "2026-05-06",
        "editor": "Wyna Liu",
        "illustrator": "Glenn Harvey",
        "categories": [{"title": "Things", "cards": [image_card, {"content": "BELL", "position": 0}]}],
    }
    puzzle = NYTGamesClient(session=session).connections("2026-05-06")
    image, word = puzzle.categories[0].cards
    assert puzzle.illustrator == "Glenn Harvey"
    assert image.content is None
    assert image.image_alt_text == "SLOT MACHINE"
    assert image.text == "SLOT MACHINE"
    assert word.text == "BELL"
