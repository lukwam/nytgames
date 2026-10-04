"""NYT Games models."""
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
    """Connections Puzzle Card."""
    content: str
    position: int


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
    player: dict | None = None
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
    freeExpiration: int
    outerLetters: List[str]
    pangrams: List[str]
    printDate: str
    validLetters: List[str]


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
    """Spelling Bee Ranks."""
    Amazing: int
    Beginner: int
    Genius: int
    Good: int
    Good_Start: int = Field(..., alias="Good Start")
    Great: int
    Moving_Up: int = Field(..., alias="Moving Up")
    Nice: int
    Queen_Bee: int = Field(..., alias="Queen Bee")
    Solid: int


class SpellingBeeStatsSpellingBee(NYTModel):
    """Spelling Bee Stats - Spelling Bee."""
    puzzles_started: int
    total_words: int
    total_pangrams: int
    longest_word: SpellingBeeLongestWord
    ranks: SpellingBeeRanks


class SpellingBeeStatsWordleLegacyStatsGuesses(NYTModel):
    """Spelling Bee Stats - Wordle Legacy Stats Guesses."""
    one: int = Field(..., alias="1")
    two: int = Field(..., alias="2")
    three: int = Field(..., alias="3")
    four: int = Field(..., alias="4")
    five: int = Field(..., alias="5")
    six: int = Field(..., alias="6")
    fail: int


class SpellingBeeStatsWordleLegacyStats(NYTModel):
    """Spelling Bee Stats - Wordle Legacy Stats."""
    autoOptInTimestamp: int
    currentStreak: int
    gamesPlayed: int
    gamesWon: int
    guesses: SpellingBeeStatsWordleLegacyStatsGuesses
    hasMadeStatsChoice: bool
    hasPlayed: bool
    lastWonDayOffset: int
    maxStreak: int
    timestamp: int


class SpellingBeeStatsWordle(NYTModel):
    """Spelling Bee Stats - Wordle"""
    legacyStats: SpellingBeeStatsWordleLegacyStats


class SpellingBeePlayerStats(NYTModel):
    """Spelling Bee Stats."""
    spelling_bee: SpellingBeeStatsSpellingBee
    wordle: SpellingBeeStatsWordle


class SpellingBeePlayer(NYTModel):
    """Spelling Bee Player."""
    user_id: int
    last_updated: int
    stats: SpellingBeePlayerStats


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
    player: SpellingBeePlayer


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
    player: dict | None = None
    states: List[WordleGameState]
    user_id: int
