"""NYT Games exceptions."""
import requests


class NYTGamesError(Exception):
    """Base class for NYT Games errors."""


class NYTGamesHTTPError(NYTGamesError, requests.HTTPError):
    """NYT returned an HTTP error.

    Subclasses requests.HTTPError, so code that catches that keeps working.
    """


class NYTGamesAuthenticationError(NYTGamesHTTPError):
    """NYT rejected the request as unauthenticated (HTTP 401 or 403).

    Usually the NYT-S cookie is missing or has expired.
    """


class NYTGamesNotFoundError(NYTGamesHTTPError):
    """NYT has no data for the request (HTTP 404), e.g. a date with no puzzle."""


class NYTGamesParseError(NYTGamesError, ValueError):
    """An NYT page did not contain the expected game data."""
