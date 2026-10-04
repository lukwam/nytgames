"""Date parsing for nytg, in the New York Times' time zone."""
import datetime
import zoneinfo
from collections.abc import Iterator

NYT_TIMEZONE = zoneinfo.ZoneInfo("America/New_York")

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# The first puzzle NYT serves for each game, for `--from first`.
FIRST_DATES = {
    "wordle": datetime.date(2021, 6, 19),
    "connections": datetime.date(2023, 6, 12),
    "strands": datetime.date(2024, 3, 4),
    "spelling-bee": datetime.date(2018, 5, 6),
    "letter-boxed": datetime.date(2018, 12, 17),
    "crossword-daily": datetime.date(1993, 11, 21),
    "crossword-mini": datetime.date(2014, 8, 21),
    "crossword-midi": datetime.date(2026, 2, 25),
}


def today() -> datetime.date:
    """Return today's date in New York, which is when NYT puzzles change."""
    return datetime.datetime.now(NYT_TIMEZONE).date()


def parse_date(value: str, game: str | None = None) -> datetime.date:
    """Parse a date argument.

    Accepts YYYY-MM-DD, today, yesterday, tomorrow, a weekday name (the most
    recent one, including today), or "first" for the game's first puzzle.
    Raises ValueError for anything else.
    """
    text = value.strip().lower()
    now = today()
    if text == "today":
        return now
    if text == "yesterday":
        return now - datetime.timedelta(days=1)
    if text == "tomorrow":
        return now + datetime.timedelta(days=1)
    if text in WEEKDAYS:
        return now - datetime.timedelta(days=(now.weekday() - WEEKDAYS.index(text)) % 7)
    if text == "first":
        if game not in FIRST_DATES:
            raise ValueError('"first" is only available for a specific game')
        return FIRST_DATES[game]
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError(
            f"Invalid date {value!r}: use YYYY-MM-DD, today, yesterday, tomorrow or a weekday"
        ) from None


def date_range(start: datetime.date, end: datetime.date) -> Iterator[datetime.date]:
    """Yield each date from start to end, inclusive."""
    for offset in range((end - start).days + 1):
        yield start + datetime.timedelta(days=offset)


def format_seconds(seconds: int | None) -> str:
    """Format a duration as M:SS or H:MM:SS."""
    if seconds is None:
        return ""
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02}:{secs:02}" if hours else f"{minutes}:{secs:02}"
