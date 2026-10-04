"""NYT Games models."""
import datetime
from enum import Enum
from typing import Dict
from typing import List
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class NYTModel(BaseModel):
    """Base model for NYT responses.

    Extra fields are allowed and passed through so that new fields added by
    NYT do not break validation.
    """
    model_config = ConfigDict(extra="allow")


class ConnectionsPuzzleCard(NYTModel):
    """Connections Puzzle Card.

    Most cards are words (`content`). Picture puzzles use image cards instead,
    with `image_url` and `image_alt_text`, and a puzzle can mix both.
    """
    content: str | None = None
    image_alt_text: str | None = None
    image_url: str | None = None
    position: int

    @property
    def text(self) -> str | None:
        """The card's word, or the alt text for an image card."""
        return self.content if self.content is not None else self.image_alt_text


class ConnectionsPuzzleCategory(NYTModel):
    """Connections Puzzle Category."""
    title: str
    cards: List[ConnectionsPuzzleCard]


class ConnectionsPuzzle(NYTModel):
    """Connections Puzzle."""
    id: int
    status: str
    print_date: str
    editor: str
    illustrator: str | None = None
    categories: List[ConnectionsPuzzleCategory]


class CrosswordGameData(NYTModel):
    """Crossword Game Data (the user's saved progress)."""
    cells: dict
    completionFraction: float | None = None
    firstSolve: int | None = None
    firstSolveDate: str | None = None
    playTimeSeconds: int | None = None
    star: str | None = None


class CrosswordGameState(NYTModel):
    """Crossword Game State."""
    game: str
    game_data: CrosswordGameData
    print_date: str
    puzzle_id: str
    timestamp: int
    user_id: int


class CrosswordGame(NYTModel):
    """Crossword Game States."""
    player: "Player | None" = None
    states: List[CrosswordGameState]
    user_id: int


class CrosswordPuzzleCell(NYTModel):
    """Crossword Puzzle Cell."""
    answer: str | None = None
    clues: List[int] | None = None
    label: int | None = None
    # Rebus squares list other accepted answers, e.g. {"valid": ["L"]}.
    moreAnswers: Dict[str, List[str]] | None = None
    type: int | None = None


class CrosswordPuzzleClue(NYTModel):
    """Crossword Puzzle Clue."""
    cells: List[int]
    direction: str
    label: str
    list: int | None = None
    relatives: List[int] | None = None
    text: List[Dict[str, str]]


class CrosswordPuzzleClueList(NYTModel):
    """Crossword Puzzle Clue List."""
    clues: List[int]
    name: str


class CrosswordPuzzleBody(NYTModel):
    """Crossword Puzzle Body."""
    board: str
    cells: List[CrosswordPuzzleCell]
    clues: List[CrosswordPuzzleClue]
    clueLists: List[CrosswordPuzzleClueList]
    dimensions: Dict[str, int]
    SVG: dict


class CrosswordPuzzle(NYTModel):
    """Crossword Puzzle (v6 format used by Daily, Mini, Midi and Bonus)."""
    id: int
    body: List[CrosswordPuzzleBody]
    constructors: List[str]
    copyright: str
    editor: str | None = None
    freePuzzle: bool | None = None
    lastUpdated: str
    notes: list | None = None
    publicationDate: str
    relatedContent: dict | None = None
    subcategory: int | None = None
    title: str | None = None


class CrosswordOraclePuzzle(NYTModel):
    """Crossword Oracle Puzzle."""
    print_date: str
    published: str
    puzzle_id: int
    time_delta: int


class CrosswordOracleResults(NYTModel):
    """Crossword Oracle Results."""
    current: CrosswordOraclePuzzle
    next: CrosswordOraclePuzzle


class CrosswordOracle(NYTModel):
    """Crossword Oracle (current and next puzzle)."""
    results: CrosswordOracleResults
    status: str


# pylint: disable=invalid-name
class CrosswordPublishType(str, Enum):
    """Crossword Publish Type."""
    daily = "daily"
    bonus = "bonus"
    midi = "midi"
    mini = "mini"


class CrosswordPuzzleListItem(NYTModel):
    """Crossword Puzzle."""
    author: str
    editor: str
    format_type: str
    percent_filled: int
    print_date: str
    publish_type: str
    puzzle_id: int
    solved: bool
    star: str | None = None
    title: str
    version: int


class CrosswordPuzzlesList(NYTModel):
    """Crossword Puzzle List."""
    results: List[CrosswordPuzzleListItem]
    status: str


class ArchiveGame(str, Enum):
    """Games available from the games archive (``NYTGamesClient.archive``)."""
    connections = "connections"
    crossword_daily = "crossword_daily"
    crossword_midi = "crossword_midi"
    crossword_mini = "crossword_mini"
    strands = "strands"
    wordle = "wordle"


class ArchivePuzzle(NYTModel):
    """A puzzle in the games archive.

    Other fields depend on the game: crosswords have ``byline``, Strands has
    ``constructor`` and ``word_count``, and Wordle includes ``solution`` and
    ``days_since_launch``. They are kept as extra fields.
    """
    id: int
    print_date: str
    editor: str | None = None
    byline: str | None = None


class LetterBoxedPuzzle(NYTModel):
    """Letter Boxed Puzzle."""
    id: int
    dictionary: List[str]
    editor: str | None = None
    ourSolution: List[str]
    par: int
    printDate: str
    sides: List[str]


class SpellingBeeGameDay(NYTModel):
    """Spelling Bee Game Day."""
    id: int
    answers: List[str]
    centerLetter: str
    displayDate: str
    displayWeekday: str
    editor: str
    freeExpiration: int | None = None
    outerLetters: List[str]
    pangrams: List[str]
    printDate: str
    validLetters: List[str]


class SpellingBeePuzzle(NYTModel):
    """Spelling Bee Puzzle from the dated svc/spelling-bee/v1 endpoint.

    Note that `answers` does not include the pangrams. Use to_game_day() to get
    the same shape as the game page, with the full word list.
    """
    id: int
    answers: List[str]
    center_letter: str
    editor: str
    outer_letters: str
    pangrams: List[str]
    print_date: str

    def to_game_day(self) -> SpellingBeeGameDay:
        """Return the puzzle in the game page format.

        `answers` lists the pangrams first, as the game page does.
        `freeExpiration` is not available and is left unset.
        """
        date = datetime.date.fromisoformat(self.print_date)
        outer_letters = list(self.outer_letters)
        return SpellingBeeGameDay(
            id=self.id,
            answers=[*self.pangrams, *self.answers],
            centerLetter=self.center_letter,
            displayDate=f"{date:%B} {date.day}, {date.year}",
            displayWeekday=f"{date:%A}",
            editor=self.editor,
            outerLetters=outer_letters,
            pangrams=self.pangrams,
            printDate=self.print_date,
            validLetters=[self.center_letter, *outer_letters],
        )


class SpellingBeeGamePastPuzzles(NYTModel):
    """Spelling Bee Game Past Puzzles."""
    today: SpellingBeeGameDay
    yesterday: SpellingBeeGameDay
    lastWeek: List[SpellingBeeGameDay]
    thisWeek: List[SpellingBeeGameDay]


class SpellingBeeGameData(NYTModel):
    """Spelling Bee Game Data."""
    today: SpellingBeeGameDay
    yesterday: SpellingBeeGameDay
    pastPuzzles: SpellingBeeGamePastPuzzles


class SpellingBeeLongestWord(NYTModel):
    """Spelling Bee Longest Word"""
    word: str
    center_letter: str
    print_date: str


class SpellingBeeRanks(NYTModel):
    """Spelling Bee Ranks (number of puzzles finished at each rank)."""
    Amazing: int = 0
    Beginner: int = 0
    Genius: int = 0
    Good: int = 0
    Good_Start: int = Field(0, alias="Good Start")
    Great: int = 0
    Moving_Up: int = Field(0, alias="Moving Up")
    Nice: int = 0
    Queen_Bee: int = Field(0, alias="Queen Bee")
    Solid: int = 0


# Player stats
#
# These mirror the `player.stats` object NYT returns from the game state
# service. A game's stats are only present once the user has played it.


class SpellingBeeStats(NYTModel):
    """Spelling Bee Stats."""
    puzzles_started: int
    total_words: int
    total_pangrams: int
    longest_word: SpellingBeeLongestWord | None = None
    ranks: SpellingBeeRanks


class WordleGuesses(NYTModel):
    """Wordle wins by number of guesses."""
    one: int = Field(0, alias="1")
    two: int = Field(0, alias="2")
    three: int = Field(0, alias="3")
    four: int = Field(0, alias="4")
    five: int = Field(0, alias="5")
    six: int = Field(0, alias="6")
    fail: int = 0


class WordleLegacyStats(NYTModel):
    """Wordle Legacy Stats (daily games, including pre-NYT account history)."""
    currentStreak: int
    gamesPlayed: int
    gamesWon: int
    guesses: WordleGuesses
    hasPlayed: bool | None = None
    lastWonDayOffset: int | None = None
    maxStreak: int


class WordleCalculatedStats(NYTModel):
    """Wordle Calculated Stats (current streaks by print date)."""
    currentStreak: int
    hasPlayed: bool | None = None
    lastCompletedPrintDate: str | None = None
    lastWonPrintDate: str | None = None
    maxStreak: int


class WordleTotalStats(NYTModel):
    """Wordle Total Stats (all games, including the archive)."""
    gamesPlayed: int
    gamesWon: int
    guesses: WordleGuesses
    hasPlayed: bool | None = None
    hasPlayedArchive: bool | None = None


class WordleStats(NYTModel):
    """Wordle Stats.

    NYT reports three overlapping sets of Wordle stats that can disagree (for
    example the legacy and calculated current streaks), so they are kept
    separate rather than merged.
    """
    calculatedStats: WordleCalculatedStats | None = None
    legacyStats: WordleLegacyStats | None = None
    totalStats: WordleTotalStats | None = None


class ConnectionsStats(NYTModel):
    """Connections Stats."""
    current_streak: int
    last_played_print_date: str | None = None
    max_streak: int
    # Number of puzzles finished with 0 to 4 mistakes.
    mistakes: Dict[str, int]
    puzzles_completed: int
    puzzles_won: int


class StrandsStats(NYTModel):
    """Strands Stats."""
    current_streak: int
    last_played_print_date: str | None = None
    max_streak: int
    no_hints: int
    puzzles_completed: int
    puzzles_started: int
    spangram_first: int


class CrosswordStreak(NYTModel):
    """Crossword Streak."""
    current: int
    longest: int
    startDate: str | None = None


class CrosswordBestTime(NYTModel):
    """Crossword Best Time."""
    date: str | None = None
    timeSeconds: int


class CrosswordDayStats(NYTModel):
    """Crossword Daily Stats for one day of the week."""
    avgTimeSeconds: int
    best: CrosswordBestTime | None = None
    latestDate: str | None = None
    latestTimeSeconds: int | None = None
    thisWeeksDate: str | None = None
    thisWeeksTime: int | None = None
    totalSolveTime: int
    totalSolves: int
    verticalStreak: CrosswordStreak | None = None


class CrosswordDailyStats(NYTModel):
    """Crossword Daily Stats."""
    # Keyed by lowercase day of the week ("monday" to "sunday").
    dailyStats: Dict[str, CrosswordDayStats]
    dailyStreaks: CrosswordStreak | None = None
    puzzlesSolved: int
    puzzlesStarted: int
    solveRate: float


class CrosswordMiniStats(NYTModel):
    """Crossword Mini and Midi Stats."""
    avgTimeSeconds: int
    bestDate: str | None = None
    bestTimeSeconds: int | None = None
    puzzlesSolved: int
    puzzlesStarted: int
    solveRate: float
    streaks: CrosswordStreak | None = None


class PlayerStats(NYTModel):
    """Player Stats for every game the user has played."""
    connections: ConnectionsStats | None = None
    crossword_daily: CrosswordDailyStats | None = None
    crossword_midi: CrosswordMiniStats | None = None
    crossword_mini: CrosswordMiniStats | None = None
    spelling_bee: SpellingBeeStats | None = None
    strands: StrandsStats | None = None
    wordle: WordleStats | None = None


class Player(NYTModel):
    """Player."""
    account_creation_date: str | None = None
    last_updated: int | None = None
    stats: PlayerStats = PlayerStats()
    user_id: int | None = None


# Names used before the player stats models were shared across games.
SpellingBeeStatsSpellingBee = SpellingBeeStats
SpellingBeeStatsWordleLegacyStatsGuesses = WordleGuesses
SpellingBeeStatsWordleLegacyStats = WordleLegacyStats
SpellingBeeStatsWordle = WordleStats
SpellingBeePlayerStats = PlayerStats
SpellingBeePlayer = Player


class SpellingBeeLatestStateGameData(NYTModel):
    """Spelling Bee Latest State Game Data."""
    answers: List[str]
    isRevealed: bool
    rank: str


class SpellingBeeLatestState(NYTModel):
    """Spelling Bee Latest State."""
    game_data: SpellingBeeLatestStateGameData
    game: str
    print_date: str
    puzzle_id: str
    schema_version: str
    timestamp: int
    user_id: int
    version: str


class SpellingBeeLatest(NYTModel):
    """Spelling Bee Latest."""
    user_id: int
    states: List[SpellingBeeLatestState]
    player: Player


class StrandsPuzzle(NYTModel):
    """Strands Puzzle."""
    id: int
    clue: str
    constructors: str | None = None
    editor: str
    printDate: str
    solutions: List[str]
    spangram: str
    startingBoard: List[str]
    themeCoords: Dict[str, List[List[int]]]
    spangramCoords: List[List[int]] | None = None
    themeWords: List[str] | None = []


class WordlePuzzle(NYTModel):
    """Wordle Puzzle."""
    id: int
    days_since_launch: int | None = None
    editor: str | None = None
    print_date: str
    solution: str


class WordleGameData(NYTModel):
    """Wordle Game Data (the user's saved progress)."""
    boardState: List[str]
    currentRowIndex: int
    hardMode: bool | None = None
    isPlayingArchive: bool | None = None
    status: str


class WordleGameState(NYTModel):
    """Wordle Game State."""
    game: str
    game_data: WordleGameData
    print_date: str
    puzzle_id: str
    schema_version: str | None = None
    timestamp: int
    user_id: int
    version: str | None = None


class WordlePuzzlesList(NYTModel):
    """Wordle Game States."""
    player: Player | None = None
    states: List[WordleGameState]
    user_id: int


CrosswordGame.model_rebuild()
