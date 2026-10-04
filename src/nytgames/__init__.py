"""Unofficial client for the New York Times Games APIs."""
__version__ = "0.7.0"

from nytgames.client import NYTGamesClient  # noqa: E402
from nytgames.client import parse_cookies  # noqa: E402
from nytgames.exceptions import NYTGamesAuthenticationError  # noqa: E402
from nytgames.exceptions import NYTGamesError  # noqa: E402
from nytgames.exceptions import NYTGamesExportError  # noqa: E402
from nytgames.exceptions import NYTGamesHTTPError  # noqa: E402
from nytgames.exceptions import NYTGamesNotFoundError  # noqa: E402
from nytgames.exceptions import NYTGamesParseError  # noqa: E402
from nytgames.exceptions import NYTGamesRateLimitError  # noqa: E402
from nytgames.models import ArchiveGame  # noqa: E402
from nytgames.models import CrosswordPublishType  # noqa: E402
from nytgames.spelling_bee import spelling_bee_hints  # noqa: E402

__all__ = [
    "ArchiveGame",
    "CrosswordPublishType",
    "NYTGamesAuthenticationError",
    "NYTGamesClient",
    "NYTGamesError",
    "NYTGamesExportError",
    "NYTGamesHTTPError",
    "NYTGamesNotFoundError",
    "NYTGamesParseError",
    "NYTGamesRateLimitError",
    "parse_cookies",
    "spelling_bee_hints",
]
