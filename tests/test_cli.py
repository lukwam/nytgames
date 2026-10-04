"""nytg command line tests.

The NYT client is replaced with a mock, so these run offline.
"""
import datetime
import json
import stat
import sys
from unittest import mock

import pytest
import requests
from typer.testing import CliRunner

from nytgames import NYTGamesAuthenticationError
from nytgames import NYTGamesNotFoundError
from nytgames.cli import dates
from nytgames.cli import app as cli_main
from nytgames.cli import output
from nytgames.cli.state import State
from nytgames.models import ConnectionsPuzzle
from nytgames.models import CrosswordGame
from nytgames.models import CrosswordPuzzlesList
from nytgames.models import Player
from nytgames.models import WordlePuzzle

runner = CliRunner()

WORDLE = WordlePuzzle(id=919, days_since_launch=1454, editor="Tracy Bennett",
                      print_date="2025-06-12", solution="vixen")
CONNECTIONS = ConnectionsPuzzle(
    id=1, status="OK", print_date="2025-06-12", editor="Wyna Liu",
    categories=[
        {"title": f"GROUP {g}", "cards": [{"content": f"W{g}{i}", "position": g * 4 + i} for i in range(4)]}
        for g in range(4)
    ],
)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Use a temporary config directory and no cookies from the environment."""
    monkeypatch.setenv("NYTG_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv("NYT_COOKIES", raising=False)
    monkeypatch.delenv("NYTG_PROFILE", raising=False)
    monkeypatch.setattr(dates, "today", lambda: datetime.date(2026, 10, 4))
    output.default_format = None


@pytest.fixture
def client(monkeypatch):
    """Replace the CLI's NYT client with a mock."""
    fake = mock.Mock()
    monkeypatch.setattr(State, "client", lambda self: fake)
    return fake


def run(*args):
    return runner.invoke(cli_main.app, list(args))


@pytest.mark.parametrize("text,expected", [
    ("today", "2026-10-04"),
    ("yesterday", "2026-10-03"),
    ("tomorrow", "2026-10-05"),
    ("sunday", "2026-10-04"),
    ("friday", "2026-10-02"),
    ("2025-06-12", "2025-06-12"),
])
def test_parse_date(text, expected):
    assert dates.parse_date(text).isoformat() == expected


def test_parse_date_first_and_errors():
    assert dates.parse_date("first", "wordle") == datetime.date(2021, 6, 19)
    with pytest.raises(ValueError):
        dates.parse_date("first")
    with pytest.raises(ValueError):
        dates.parse_date("someday")


def test_wordle_hides_the_answer_unless_asked(client):
    client.wordle.return_value = WORDLE

    hidden = json.loads(run("wordle", "2025-06-12", "-f", "json").stdout)
    shown = json.loads(run("wordle", "2025-06-12", "--answers", "-f", "json").stdout)

    assert "solution" not in hidden
    assert shown["solution"] == "vixen"
    client.wordle.assert_called_with("2025-06-12")


def test_value_format(client):
    client.wordle.return_value = WORDLE
    result = run("wordle", "2025-06-12", "-a", "-f", "value(solution,number)")
    assert result.stdout == "vixen\t1454\n"


def test_root_format_option_and_yaml(client):
    client.wordle.return_value = WORDLE
    result = run("-f", "yaml", "wordle", "2025-06-12")
    assert "number: 1454" in result.stdout


def test_connections_board_and_groups(client):
    client.connections.return_value = CONNECTIONS

    board = json.loads(run("connections", "2025-06-12", "-f", "json").stdout)
    groups = json.loads(run("connections", "2025-06-12", "-a", "-f", "json").stdout)

    assert board["board"][0] == ["W00", "W01", "W02", "W03"]
    assert "categories" not in board
    assert groups["categories"][3] == {"title": "GROUP 3", "cards": ["W30", "W31", "W32", "W33"]}


def test_csv_flattens_nested_values(client):
    client.connections.return_value = CONNECTIONS
    result = run("connections", "2025-06-12", "-f", "csv")
    header, row = result.stdout.splitlines()
    assert header == "date,id,editor,board"
    assert row.startswith("2025-06-12,1,Wyna Liu,")


def test_bad_format_fails_before_calling_nyt(client):
    result = run("wordle", "-f", "xml")
    assert result.exit_code == 2
    client.wordle.assert_not_called()


def test_bad_date_is_a_usage_error(client):
    result = run("wordle", "someday")
    assert result.exit_code == 2
    assert "Invalid date" in result.output


@pytest.mark.parametrize("error,message", [
    (NYTGamesNotFoundError("404", response=mock.Mock(status_code=404)), "no puzzle"),
    (NYTGamesAuthenticationError("403", response=mock.Mock(status_code=403)), "nytg auth login"),
])
def test_main_reports_nyt_errors(client, monkeypatch, capsys, error, message):
    client.wordle.side_effect = error
    monkeypatch.setattr(sys, "argv", ["nytg", "wordle", "1900-01-01"])
    with pytest.raises(SystemExit) as exit_info:
        cli_main.main()
    assert exit_info.value.code == 1
    assert message in capsys.readouterr().err


def test_auth_login_saves_only_nyt_s(tmp_path, monkeypatch):
    export = tmp_path / "cookies.json"
    export.write_text(json.dumps([{"name": "NYT-S", "value": "secret"}, {"name": "other", "value": "x"}]))
    with mock.patch("nytgames.cli.settings.NYTGamesClient") as client_class:
        client_class.return_value.player_stats.return_value = Player(user_id=123)
        result = run("auth", "login", "--from-file", str(export))

    assert result.exit_code == 0, result.output
    config = tmp_path / "config" / "config.ini"
    assert "cookies = NYT-S=secret" in config.read_text()
    assert "other" not in config.read_text()
    assert stat.S_IMODE(config.stat().st_mode) == 0o600


def test_auth_login_rejected_cookies_are_not_saved(tmp_path):
    with mock.patch("nytgames.cli.settings.NYTGamesClient") as client_class:
        client_class.return_value.player_stats.side_effect = NYTGamesAuthenticationError(
            "403", response=mock.Mock(status_code=403))
        result = runner.invoke(cli_main.app, ["auth", "login"], input="NYT-S=bad\n")

    assert result.exit_code == 1
    assert not (tmp_path / "config" / "config.ini").exists()


def test_cookie_precedence(monkeypatch):
    state = State()
    state.config.set("default", "cookies", "NYT-S=from-config")
    assert state.resolve_cookies() == ("NYT-S=from-config", "profile 'default'")
    monkeypatch.setenv("NYT_COOKIES", "NYT-S=from-env")
    assert state.resolve_cookies()[1] == "NYT_COOKIES"
    state.cookies = "NYT-S=from-flag"
    assert state.resolve_cookies()[1] == "--cookies"


def test_config_and_profiles():
    assert run("-p", "alice", "config", "set", "format", "json").exit_code == 0
    assert run("-p", "alice", "config", "get", "format").stdout == "json\n"
    assert run("config", "get", "format").exit_code == 1

    assert run("config", "profiles", "activate", "alice").exit_code == 0
    profiles = json.loads(run("config", "profiles", "list", "-f", "json").stdout)
    assert {"name": "alice", "active": True, "cookies": False} in profiles

    assert run("config", "profiles", "delete", "alice").exit_code == 0
    assert run("config", "get", "format").exit_code == 1
    assert run("config", "set", "colour", "red").exit_code == 2


def test_profile_format_is_the_default(client):
    client.wordle.return_value = WORDLE
    run("config", "set", "format", "json")
    assert json.loads(run("wordle", "2025-06-12").stdout)["number"] == 1454


def test_archive_saves_skips_and_reports_missing(client, tmp_path):
    def wordle(day):
        if day == "2025-06-11":
            raise NYTGamesNotFoundError("404", response=mock.Mock(status_code=404))
        return WORDLE

    client.wordle.side_effect = wordle
    out = tmp_path / "archive"
    (out / "wordle").mkdir(parents=True)
    (out / "wordle" / "2025-06-13.json").write_text("{}")

    result = run("archive", "wordle", "--from", "2025-06-11", "--to", "2025-06-13",
                 "-o", str(out), "--delay", "0", "-f", "json")

    summary = json.loads(result.stdout)
    assert (summary["saved"], summary["skipped"], summary["missing"]) == (1, 1, ["2025-06-11"])
    assert json.loads((out / "wordle" / "2025-06-12.json").read_text())["solution"] == "vixen"
    assert (out / "wordle" / "2025-06-13.json").read_text() == "{}"


def test_history_crossword_fetches_the_list_in_windows(client):
    client.crossword_puzzles.return_value = CrosswordPuzzlesList(results=[], status="OK")
    client.crossword_game.return_value = CrosswordGame(user_id=1, states=[])

    result = run("history", "crossword", "--from", "2026-01-01", "--to", "2026-06-30", "-f", "json")

    assert result.exit_code == 0, result.output
    windows = [(c.kwargs["date_start"], c.kwargs["date_end"]) for c in client.crossword_puzzles.call_args_list]
    assert windows == [("2026-01-01", "2026-03-31"), ("2026-04-01", "2026-06-29"), ("2026-06-30", "2026-06-30")]


def test_history_midi_reads_each_puzzle_and_its_game_state(client):
    puzzle = mock.Mock(id=23834, constructors=["Paolo Pasco"], model_extra={})
    client.crossword.return_value = puzzle
    client.crossword_game.return_value = CrosswordGame(user_id=1, states=[{
        "game": "crossword_midi", "print_date": "2026-10-04", "puzzle_id": "23834",
        "timestamp": 0, "user_id": 1,
        "game_data": {"cells": {}, "firstSolve": 1, "completionFraction": 1, "playTimeSeconds": 227,
                      "star": "gold"},
    }])

    result = run("history", "crossword", "midi", "--from", "2026-10-04", "--to", "2026-10-04", "-f", "json")

    row = json.loads(result.stdout)[0]
    assert (row["solved"], row["seconds"], row["star"], row["author"]) == (True, 227, "gold", "Paolo Pasco")
    client.crossword_puzzles.assert_not_called()


def test_cli_extra_message_when_typer_is_missing(monkeypatch):
    import nytgames.cli

    monkeypatch.setitem(sys.modules, "nytgames.cli.app", None)
    with pytest.raises(SystemExit) as exit_info:
        nytgames.cli.main()
    assert "nytimes-games[cli]" in str(exit_info.value)


def test_request_errors_are_reported(client, monkeypatch, capsys):
    client.wordle.side_effect = requests.ConnectionError("offline")
    monkeypatch.setattr(sys, "argv", ["nytg", "wordle"])
    with pytest.raises(SystemExit):
        cli_main.main()
    assert "Request to NYT failed" in capsys.readouterr().err
