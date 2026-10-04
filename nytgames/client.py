"""NYT Games client."""
import json
import logging
import re
from typing import Any
from typing import Iterable
from typing import Mapping

import requests
from bs4 import BeautifulSoup

from nytgames.models import ConnectionsPuzzle
from nytgames.models import CrosswordGame
from nytgames.models import CrosswordOracle
from nytgames.models import CrosswordPublishType
from nytgames.models import CrosswordPuzzle
from nytgames.models import CrosswordPuzzlesList
from nytgames.models import SpellingBeeGameData
from nytgames.models import SpellingBeeGameDay
from nytgames.models import SpellingBeeLatest
from nytgames.models import StrandsPuzzle
from nytgames.models import WordlePuzzle
from nytgames.models import WordlePuzzlesList

logger = logging.getLogger(__name__)

NYT_BASE_URL = "https://www.nytimes.com"

Cookies = Mapping[str, str] | Iterable[Mapping[str, Any]] | str | None


def parse_cookies(cookies: Cookies) -> dict[str, str]:
    """Return cookies as a dict.

    Accepts a dict of cookie names to values, a list of cookie objects with
    `name` and `value` keys (the Cookie-Editor JSON export format), or a
    `Cookie` header string such as `"NYT-S=...; nyt-a=..."`.
    """
    if not cookies:
        return {}
    if isinstance(cookies, str):
        parsed = {}
        for part in cookies.split(";"):
            name, sep, value = part.strip().partition("=")
            if sep:
                parsed[name] = value
        return parsed
    if isinstance(cookies, Mapping):
        return dict(cookies)
    return {cookie["name"]: cookie["value"] for cookie in cookies}


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

    HTTP errors from NYT are raised as `requests.HTTPError`.
    """

    def __init__(
        self,
        cookies: Cookies = None,
        session: requests.Session | None = None,
        timeout: float = 30,
    ):
        self.cookies = parse_cookies(cookies)
        self.session = session or requests.Session()
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None, json_response: bool = True):
        """Return the response from a GET request to NYT."""
        headers = {"Accept": "application/json"} if json_response else {}
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        response = self.session.get(
            f"{NYT_BASE_URL}{path}",
            cookies=self.cookies,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )
        logger.info("GET %s", response.request.url)
        response.raise_for_status()
        return response.json() if json_response else response

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

    def crossword_puzzles(
        self,
        publish_type: CrosswordPublishType | str | None = None,
        sort_order: str | None = None,
        sort_by: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> CrosswordPuzzlesList:
        """Return a list of crossword puzzles, including the user's progress."""
        if publish_type is not None:
            publish_type = CrosswordPublishType(publish_type).value
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
        puzzle_id: int | str,
        publish_type: CrosswordPublishType | str = CrosswordPublishType.daily,
    ) -> CrosswordGame:
        """Return the user's saved game state for a crossword puzzle.

        `states` is empty if the user has not played the puzzle.
        """
        publish_type = CrosswordPublishType(publish_type).value
        response = self._get(
            f"/svc/games/state/crossword_{publish_type}/latests",
            params={"puzzle_ids": str(puzzle_id)},
        )
        return CrosswordGame(**response)

    def crossword_oracle(
        self,
        publish_type: CrosswordPublishType | str = CrosswordPublishType.daily,
    ) -> CrosswordOracle:
        """Return the current and next crossword puzzle (daily, mini or midi)."""
        publish_type = CrosswordPublishType(publish_type).value
        return CrosswordOracle(**self._get(f"/svc/crosswords/v2/oracle/{publish_type}.json"))

    # Spelling Bee
    def spelling_bee(self) -> SpellingBeeGameData:
        """Return the current Spelling Bee data scraped from the game page.

        Raises ValueError if the page does not contain the game data.
        """
        response = self._get("/puzzles/spelling-bee", json_response=False)
        game_data = get_game_data(response.content)
        if game_data is None:
            raise ValueError("Spelling Bee game data not found in the page")
        return SpellingBeeGameData(**game_data)

    def spelling_bee_puzzles(self) -> dict[str, SpellingBeeGameDay]:
        """Return every Spelling Bee puzzle on the game page, keyed by print date.

        The page includes today's puzzle and the puzzles back to the start of
        last week (about two weeks). Older puzzles are not available.
        """
        game_data = self.spelling_bee()
        past = game_data.pastPuzzles
        puzzles = [game_data.today, game_data.yesterday, *past.thisWeek, *past.lastWeek]
        return {puzzle.printDate: puzzle for puzzle in sorted(puzzles, key=lambda p: p.printDate)}

    def spelling_bee_latest(self, puzzle_ids: str | None = None) -> SpellingBeeLatest:
        """Return the user's latest Spelling Bee game states.

        `puzzle_ids` is a comma separated list of up to 30 puzzle IDs (NYT
        returns HTTP 400 for more). With no IDs, `states` is empty.
        """
        response = self._get(
            "/svc/games/state/spelling_bee/latests",
            params={"puzzle_ids": puzzle_ids},
        )
        return SpellingBeeLatest(**response)

    # Strands
    def strands(self, date: str) -> StrandsPuzzle:
        """Return the Strands puzzle for a date (YYYY-MM-DD)."""
        return StrandsPuzzle(**self._get(f"/svc/strands/v2/{date}.json"))

    # Wordle
    def wordle(self, date: str) -> WordlePuzzle:
        """Return the Wordle puzzle for a date (YYYY-MM-DD)."""
        return WordlePuzzle(**self._get(f"/svc/wordle/v2/{date}.json"))

    def wordle_latest(self, puzzle_ids: str | None = None) -> WordlePuzzlesList:
        """Return the user's latest Wordle game states."""
        response = self._get(
            "/svc/games/state/wordleV2/latests",
            params={"puzzle_ids": puzzle_ids},
        )
        return WordlePuzzlesList(**response)
