"""NYT Games client."""
import datetime
import json
import logging
import re
from typing import Any
from typing import Iterable
from typing import Mapping

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from nytgames import __version__
from nytgames.exceptions import NYTGamesAuthenticationError
from nytgames.exceptions import NYTGamesHTTPError
from nytgames.exceptions import NYTGamesNotFoundError
from nytgames.exceptions import NYTGamesParseError
from nytgames.exceptions import NYTGamesRateLimitError
from nytgames.models import ArchiveGame
from nytgames.models import ArchivePuzzle
from nytgames.models import ConnectionsPuzzle
from nytgames.models import CrosswordGame
from nytgames.models import CrosswordOracle
from nytgames.models import CrosswordPublishType
from nytgames.models import CrosswordPuzzle
from nytgames.models import CrosswordPuzzlesList
from nytgames.models import LetterBoxedPuzzle
from nytgames.models import Player
from nytgames.models import SpellingBeeGameData
from nytgames.models import SpellingBeeGameDay
from nytgames.models import SpellingBeeLatest
from nytgames.models import SpellingBeePuzzle
from nytgames.models import StrandsPuzzle
from nytgames.models import WordleBotAnalysis
from nytgames.models import WordleBotSummary
from nytgames.models import WordlePuzzle
from nytgames.models import WordlePuzzlesList

logger = logging.getLogger(__name__)

NYT_BASE_URL = "https://www.nytimes.com"
WORDLEBOT_URL = "https://www.nytimes.com/svc/int/run/cubby/public-api/v1/responses/wordlebot/reader"
WORDLEBOT_SUMMARY_URL = "https://static01.nyt.com/newsgraphics/2022/wordlebot/{solution}-{date}/summary.json"
# NYT's games archive returns at most 31 days per request.
ARCHIVE_DAYS = 31
USER_AGENT = f"nytimes-games/{__version__} (+https://github.com/lukwam/nytimes-games)"

Cookies = Mapping[str, str] | Iterable[Mapping[str, Any]] | str | None
PuzzleIds = int | str | Iterable[int | str] | None


def join_puzzle_ids(puzzle_ids: PuzzleIds) -> str | None:
    """Return puzzle IDs as the comma separated string NYT expects."""
    if puzzle_ids is None or isinstance(puzzle_ids, (int, str)):
        return None if puzzle_ids is None else str(puzzle_ids)
    return ",".join(str(puzzle_id) for puzzle_id in puzzle_ids)


COOKIE_NAME = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
COOKIE_VALUE_FORBIDDEN = re.compile(r"[\x00-\x1f\x7f;]")


def parse_cookies(cookies: Cookies) -> dict[str, str]:
    """Return cookies as a dict.

    Accepts a dict of cookie names to values, a list of cookie objects with
    `name` and `value` keys (the Cookie-Editor JSON export format), either of
    those as a JSON string, or a `Cookie` header string such as
    `"NYT-S=...; nyt-a=..."`.

    Raises ValueError for cookies that can't be sent, without including any
    cookie values in the message.
    """
    if not cookies:
        return {}
    if isinstance(cookies, str):
        text = cookies.strip()
        if text.startswith(("[", "{")):
            try:
                return parse_cookies(json.loads(text))
            except json.JSONDecodeError:
                raise ValueError("The cookies look like JSON but couldn't be read as JSON") from None
        parsed = {}
        for part in text.split(";"):
            name, sep, value = part.strip().partition("=")
            if sep:
                parsed[name.strip()] = value.strip()
        return check_cookies(parsed)
    if isinstance(cookies, Mapping):
        return check_cookies({str(k): str(v) for k, v in cookies.items()})
    try:
        return check_cookies({str(c["name"]): str(c["value"]) for c in cookies})
    except (KeyError, TypeError):
        raise ValueError("Cookie lists need a name and value for each cookie") from None


def check_cookies(cookies: dict[str, str]) -> dict[str, str]:
    """Raise ValueError if any cookie can't be sent in a Cookie header.

    The message names the cookie but never includes its value.
    """
    for name, value in cookies.items():
        if not COOKIE_NAME.match(name):
            raise ValueError("A cookie has an invalid name (cookie values aren't shown)")
        if COOKIE_VALUE_FORBIDDEN.search(value):
            raise ValueError(f"The {name} cookie's value has characters that can't be sent "
                             "(such as line breaks or semicolons); its value isn't shown")
    return cookies


def retrying_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    """Return a session that retries failed requests with exponential backoff."""
    session = requests.Session()
    if retries:
        retry = Retry(
            total=retries,
            backoff_factor=backoff,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
    return session


def retry_after(response) -> float | None:
    """Return the seconds from a Retry-After header, if it has a number."""
    try:
        return float(response.headers.get("Retry-After"))
    except (TypeError, ValueError):
        return None


def get_game_data(body: bytes) -> dict | None:
    """Get Game Data from Spelling Bee Page."""
    soup = BeautifulSoup(body, "html.parser")
    script_tag = soup.find("script", string=re.compile(r"window\.gameData\s*="))
    if script_tag:
        script_content = script_tag.string
        if script_content.startswith("window.gameData = {"):
            return json.loads(script_content[len("window.gameData = "):])
    return None


class NYTGamesClient:
    """Client for the NYT Games APIs.

    Subscriber content and user game state require the `NYT-S` session cookie
    from a logged in nytimes.com browser session.

    HTTP errors from NYT are raised as NYTGamesHTTPError (a subclass of
    `requests.HTTPError`): NYTGamesAuthenticationError for 401 and 403,
    NYTGamesNotFoundError for 404 and NYTGamesRateLimitError for 429.

    Failed connections, timeouts, rate limits (429) and NYT server errors
    (500, 502, 503, 504) are retried up to `retries` times with exponential
    backoff (`backoff` seconds, doubling each time), honoring NYT's
    Retry-After header. Retries are only set up on the session the client
    creates; a `session` you pass in, such as a requests-cache session, is
    used as is.
    """

    def __init__(
        self,
        cookies: Cookies = None,
        session: requests.Session | None = None,
        timeout: float = 30,
        user_agent: str = USER_AGENT,
        retries: int = 3,
        backoff: float = 0.5,
        base_url: str = NYT_BASE_URL,
    ):
        self.cookies = parse_cookies(cookies)
        self.session = session or retrying_session(retries, backoff)
        self.timeout = timeout
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict | None = None, json_response: bool = True):
        """Return the response from a GET request to NYT.

        `path` is relative to `base_url`, or a full URL. Cookies are only sent
        to `base_url` and www.nytimes.com, never to other hosts such as NYT's
        static file server.
        """
        headers = {"User-Agent": self.user_agent}
        if json_response:
            headers["Accept"] = "application/json"
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        if path.startswith("https://"):
            url = path
            send_cookies = path.startswith((self.base_url + "/", NYT_BASE_URL + "/"))
        else:
            url, send_cookies = f"{self.base_url}{path}", True
        response = self.session.get(
            url,
            cookies=self.cookies if send_cookies else None,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )
        logger.info("GET %s", response.request.url)
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            if response.status_code == 429:
                raise NYTGamesRateLimitError(
                    str(err), response=response, retry_after=retry_after(response)
                ) from err
            error_class = {
                401: NYTGamesAuthenticationError,
                403: NYTGamesAuthenticationError,
                404: NYTGamesNotFoundError,
            }.get(response.status_code, NYTGamesHTTPError)
            raise error_class(str(err), response=response) from err
        return response.json() if json_response else response

    # Archive
    def archive(
        self,
        game: ArchiveGame | str,
        date_start: str,
        date_end: str,
    ) -> list[ArchivePuzzle]:
        """Return the puzzles published between two dates (YYYY-MM-DD), inclusive.

        `game` is connections, strands, wordle, crossword_daily, crossword_mini
        or crossword_midi. Each puzzle has its ID and print date, so this is the
        quickest way to find puzzle IDs for the game state methods. Doesn't
        need cookies. Future dates are not included.

        A few dates have two puzzles (such as 2022-12-31's daily and its 50x50
        Supermega); both are returned, so print dates can repeat.

        NYT returns at most 31 puzzles per request, so ranges are fetched 31
        days at a time, and a window that hits the limit is split and fetched
        again so no date is dropped.
        """
        game = ArchiveGame(game).value
        start = datetime.date.fromisoformat(date_start)
        end = datetime.date.fromisoformat(date_end)
        puzzles: dict[int, ArchivePuzzle] = {}
        while start <= end:
            window_end = min(start + datetime.timedelta(days=ARCHIVE_DAYS - 1), end)
            for puzzle in self._archive_window(game, start, window_end):
                puzzles.setdefault(puzzle.id, puzzle)
            start = window_end + datetime.timedelta(days=1)
        return sorted(puzzles.values(), key=lambda puzzle: (puzzle.print_date, puzzle.id))

    def _archive_window(self, game: str, start: datetime.date, end: datetime.date) -> list[ArchivePuzzle]:
        """Fetch one window, splitting it if NYT's 31 puzzle limit may have cut it short."""
        response = self._get(f"/svc/games/v1/archive/{game}/{start}/{end}")
        if len(response) < ARCHIVE_DAYS or start == end:
            return [ArchivePuzzle(**puzzle) for puzzle in response]
        middle = start + (end - start) // 2
        return (self._archive_window(game, start, middle)
                + self._archive_window(game, middle + datetime.timedelta(days=1), end))

    # Connections
    def connections(self, date: str) -> ConnectionsPuzzle:
        """Return the Connections puzzle for a date (YYYY-MM-DD)."""
        return ConnectionsPuzzle(**self._get(f"/svc/connections/v2/{date}.json"))

    # Crosswords
    def crossword(
        self,
        publish_type: CrosswordPublishType | str = CrosswordPublishType.daily,
        date: str | None = None,
    ) -> CrosswordPuzzle:
        """Return a crossword puzzle.

        `publish_type` is one of daily, mini, midi or bonus. Returns today's
        puzzle if `date` is not set (bonus puzzles require a date).
        """
        publish_type = CrosswordPublishType(publish_type).value
        path = f"/svc/crosswords/v6/puzzle/{publish_type}"
        path = f"{path}/{date}.json" if date else f"{path}.json"
        return CrosswordPuzzle(**self._get(path))

    def crossword_by_id(self, puzzle_id: int | str) -> CrosswordPuzzle:
        """Return a crossword of any type by its puzzle ID.

        Use it for dates with more than one puzzle, where crossword(date)
        returns only one of them (archive() lists both).
        """
        return CrosswordPuzzle(**self._get(f"/svc/crosswords/v6/puzzle/{puzzle_id}.json"))

    def crossword_puzzles(
        self,
        publish_type: CrosswordPublishType | str | None = None,
        sort_order: str | None = None,
        sort_by: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> CrosswordPuzzlesList:
        """Return a list of crossword puzzles, including the user's progress.

        `publish_type` is daily, mini or bonus. NYT returns at most 100 puzzles
        per request, and incomplete or empty results for long ranges, so use
        ranges of 90 days or less. NYT's list doesn't include Midi puzzles (it returns Daily
        puzzles instead), so `midi` raises ValueError; use
        archive("crossword_midi", ...) and crossword_game() for Midi puzzles.
        """
        if publish_type is not None:
            publish_type = CrosswordPublishType(publish_type).value
            if publish_type == CrosswordPublishType.midi.value:
                raise ValueError(
                    "NYT's crossword list doesn't include Midi puzzles; "
                    'use archive("crossword_midi", ...) and crossword_game() instead'
                )
        params = {
            "publish_type": publish_type,
            "sort_order": sort_order,
            "sort_by": sort_by,
            "date_start": date_start,
            "date_end": date_end,
        }
        return CrosswordPuzzlesList(**self._get("/svc/crosswords/v3/puzzles.json", params=params))

    def crossword_game(
        self,
        puzzle_id: PuzzleIds,
        publish_type: CrosswordPublishType | str = CrosswordPublishType.daily,
    ) -> CrosswordGame:
        """Return the user's saved game state for one or more crossword puzzles.

        `puzzle_id` is a puzzle ID, a comma separated string or a list of up
        to 30 IDs. `states` only includes puzzles the user has played.
        """
        publish_type = CrosswordPublishType(publish_type).value
        response = self._get(
            f"/svc/games/state/crossword_{publish_type}/latests",
            params={"puzzle_ids": join_puzzle_ids(puzzle_id)},
        )
        return CrosswordGame(**response)

    def crossword_oracle(
        self,
        publish_type: CrosswordPublishType | str = CrosswordPublishType.daily,
    ) -> CrosswordOracle:
        """Return the current and next crossword puzzle (daily, mini or midi)."""
        publish_type = CrosswordPublishType(publish_type).value
        return CrosswordOracle(**self._get(f"/svc/crosswords/v2/oracle/{publish_type}.json"))

    # Player
    def player_stats(self) -> Player:
        """Return the user's stats for every game they have played.

        Requires the NYT-S cookie. Includes the user's NYT user ID.
        """
        response = self._get(
            "/svc/games/state/wordleV2/latests",
            params={"puzzle_ids": "0"},
        )
        return Player(**response["player"])

    # Letter Boxed
    def letter_boxed(self, date: str) -> LetterBoxedPuzzle:
        """Return the Letter Boxed puzzle for a date (YYYY-MM-DD).

        Puzzles are available from 2018-12-17, and NYT also serves the next day
        or two ahead of time. A few early dates have no puzzle (2018-12-21 to
        2019-01-05 and 2019-01-25) and raise NYTGamesNotFoundError.
        """
        return LetterBoxedPuzzle(**self._get(f"/svc/letter-boxed/v1/{date}.json"))

    # Spelling Bee
    def spelling_bee(self) -> SpellingBeeGameData:
        """Return the current Spelling Bee data scraped from the game page.

        Raises ValueError if the page does not contain the game data.
        """
        response = self._get("/puzzles/spelling-bee", json_response=False)
        game_data = get_game_data(response.content)
        if game_data is None:
            raise NYTGamesParseError("Spelling Bee game data not found in the page")
        return SpellingBeeGameData(**game_data)

    def spelling_bee_puzzle(self, date: str) -> SpellingBeeGameDay:
        """Return the Spelling Bee puzzle for a date (YYYY-MM-DD).

        Puzzles are available from 2018-05-06, and NYT also serves the next
        day ahead of time. The result has the same shape as the game page
        puzzles from spelling_bee_puzzles(), including the full word list, so
        it works with spelling_bee_hints(). Dates without a puzzle raise
        NYTGamesNotFoundError.
        """
        response = self._get(f"/svc/spelling-bee/v1/{date}.json")
        return SpellingBeePuzzle(**response).to_game_day()

    def spelling_bee_puzzles(self) -> dict[str, SpellingBeeGameDay]:
        """Return every Spelling Bee puzzle on the game page, keyed by print date.

        The page includes today's puzzle and the puzzles back to the start of
        last week (about two weeks). Older puzzles are not available.
        """
        game_data = self.spelling_bee()
        past = game_data.pastPuzzles
        puzzles = [game_data.today, game_data.yesterday, *past.thisWeek, *past.lastWeek]
        return {puzzle.printDate: puzzle for puzzle in sorted(puzzles, key=lambda p: p.printDate)}

    def spelling_bee_latest(self, puzzle_ids: PuzzleIds = None) -> SpellingBeeLatest:
        """Return the user's latest Spelling Bee game states.

        `puzzle_ids` is a puzzle ID, a comma separated string or a list of up
        to 30 IDs (NYT returns HTTP 400 for more). With no IDs, `states` is
        empty.
        """
        response = self._get(
            "/svc/games/state/spelling_bee/latests",
            params={"puzzle_ids": join_puzzle_ids(puzzle_ids)},
        )
        return SpellingBeeLatest(**response)

    # Strands
    def strands(self, date: str) -> StrandsPuzzle:
        """Return the Strands puzzle for a date (YYYY-MM-DD)."""
        return StrandsPuzzle(**self._get(f"/svc/strands/v2/{date}.json"))

    # Wordle
    def wordlebot(self) -> WordleBotAnalysis | None:
        """Return your WordleBot analysis of today's Wordle, or None.

        Needs cookies. NYT only keeps today's game, and only after you've
        opened WordleBot; earlier games aren't available. When there are
        several (one each time you open WordleBot), the latest is returned.
        """
        entries = self._get(WORDLEBOT_URL)
        analyses = [
            WordleBotAnalysis(**entry["content"], created_at=entry.get("created_at"),
                              response_id=entry.get("response_id"))
            for entry in entries
            if isinstance(entry.get("content"), dict) and entry["content"].get("guesses")
        ]
        return max(analyses, key=lambda a: a.created_at or "", default=None)

    def wordlebot_summary(self, date: str, solution: str | None = None) -> WordleBotSummary:
        """Return WordleBot's summary of how everyone did on a day's Wordle.

        Available for every day since the first Wordle (2021-06-19). The files
        are named by solution, so this also fetches the day's Wordle unless
        `solution` is given. Doesn't need cookies.
        """
        solution = solution or self.wordle(date).solution
        return WordleBotSummary(**self._get(WORDLEBOT_SUMMARY_URL.format(solution=solution, date=date)))

    def wordle(self, date: str) -> WordlePuzzle:
        """Return the Wordle puzzle for a date (YYYY-MM-DD)."""
        return WordlePuzzle(**self._get(f"/svc/wordle/v2/{date}.json"))

    def wordle_latest(self, puzzle_ids: PuzzleIds = None) -> WordlePuzzlesList:
        """Return the user's latest Wordle game states.

        `puzzle_ids` is a puzzle ID, a comma separated string or a list of IDs.
        """
        response = self._get(
            "/svc/games/state/wordleV2/latests",
            params={"puzzle_ids": join_puzzle_ids(puzzle_ids)},
        )
        return WordlePuzzlesList(**response)
