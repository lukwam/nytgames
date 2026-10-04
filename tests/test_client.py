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
