"""Tests for the public CLI extension API in nytgames.cli.extension."""
import datetime
import json
import sys
from unittest import mock

import pytest
import typer
from typer.testing import CliRunner

import nytgames.cli
from nytgames import NYTGamesAuthenticationError
from nytgames import NYTGamesNotFoundError
from nytgames.cli import dates
from nytgames.cli import extension
from nytgames.cli import output
from nytgames.cli.extension import FormatOption
from nytgames.cli.extension import create_app
from nytgames.cli.extension import emit
from nytgames.cli.extension import run
from nytgames.models import WordlePuzzle

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NYTG_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv("NYT_COOKIES", raising=False)
    monkeypatch.delenv("NYTG_PROFILE", raising=False)
    monkeypatch.setattr(dates, "today", lambda: datetime.date(2026, 10, 4))
    output.default_format = None


def tool_app() -> typer.Typer:
    """An extension app with a db group, like nyt-puzzles' nytp."""
    app = create_app(name="nytp", help="NYT puzzles archive tools.", version="9.9.9")
    db = typer.Typer(help="Query the archive.")
    app.add_typer(db, name="db")

    @db.command("whoami")
    def whoami(fmt: FormatOption = None) -> None:
        cookies, source = extension.resolve_cookies()
        emit({"profile": extension.active_profile(), "cookies": cookies, "source": source}, fmt)

    @db.command("wordle")
    def db_wordle(date: str = "today", fmt: FormatOption = None) -> None:
        day = extension.parse_date(date, "wordle")
        puzzle = extension.get_client().wordle(day.isoformat())
        emit({"date": puzzle.print_date, "id": puzzle.id}, fmt)

    return app


def test_create_app_returns_independent_apps():
    tool = tool_app()
    plain = create_app()

    assert runner.invoke(tool, ["db", "whoami"]).exit_code == 0
    assert runner.invoke(plain, ["db", "whoami"]).exit_code == 2

    tool_config = next(g.typer_instance for g in tool.registered_groups if g.name == "config")
    plain_config = next(g.typer_instance for g in plain.registered_groups if g.name == "config")
    assert tool_config is not plain_config


def test_extension_app_has_every_nytg_command():
    def names(app):
        return ({c.name for c in app.registered_commands}
                | {g.name for g in app.registered_groups})

    assert names(create_app()) <= names(tool_app())
    assert {"wordle", "crossword", "stats", "archive", "auth", "config", "history", "db"} <= names(tool_app())


def test_name_help_and_version():
    app = tool_app()
    assert runner.invoke(app, ["--version"]).stdout == "nytp 9.9.9\n"
    assert "NYT puzzles archive tools." in runner.invoke(app, ["--help"]).stdout


def test_extension_commands_get_root_options():
    result = runner.invoke(tool_app(), ["--profile", "alice", "--cookies", "NYT-S=x", "-f", "json", "db", "whoami"])
    assert json.loads(result.stdout) == {"profile": "alice", "cookies": "NYT-S=x", "source": "--cookies"}


def test_extension_commands_use_the_client_and_formats(monkeypatch):
    client = mock.Mock()
    client.wordle.return_value = WordlePuzzle(id=919, print_date="2025-06-12", solution="vixen")
    monkeypatch.setattr(extension.state, "client", lambda: client)

    result = runner.invoke(tool_app(), ["db", "wordle", "--date", "2025-06-12", "-f", "value(id)"])

    assert result.stdout == "919\n"
    assert runner.invoke(tool_app(), ["db", "wordle", "--date", "someday"]).exit_code == 2


@pytest.mark.parametrize("error,message", [
    (NYTGamesAuthenticationError("403", response=mock.Mock(status_code=403)), "nytp auth login"),
    (NYTGamesNotFoundError("404", response=mock.Mock(status_code=404)), "no puzzle"),
])
def test_run_maps_nyt_errors_to_exit_codes(monkeypatch, capsys, error, message):
    app = tool_app()

    @app.command("boom")
    def boom() -> None:
        raise error

    monkeypatch.setattr(sys, "argv", ["nytp", "boom"])
    with pytest.raises(SystemExit) as exit_info:
        run(app)
    assert exit_info.value.code == 1
    assert message in capsys.readouterr().err


def test_create_app_and_run_are_importable_from_nytgames_cli():
    assert nytgames.cli.create_app is create_app
    assert nytgames.cli.run is run
    with pytest.raises(AttributeError):
        nytgames.cli.something_else  # noqa: B018
