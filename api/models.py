"""NYT Games API models module."""
from enum import Enum
from typing import Dict
from typing import List
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ConnectionsPuzzleCard(BaseModel):
    """Connections Puzzle Card."""
    content: str
    position: int

    model_config = ConfigDict(extra="forbid")


class ConnectionsPuzzleCategory(BaseModel):
    """Connections Puzzle Category."""
    title: str
    cards: List[ConnectionsPuzzleCard]

    model_config = ConfigDict(extra="forbid")


class ConnectionsPuzzle(BaseModel):
    """Connections Puzzle."""
    id: int
    status: str
    print_date: str
    editor: str
    categories: List[ConnectionsPuzzleCategory]

    model_config = ConfigDict(extra="forbid")


class CrosswordGameResult(BaseModel):
    """Crossword Game."""
    id: str
    board: List[str]
    completed: bool
    eligible: bool
    epoch: int
    firstOpened: int
    firstSolved: int
    isPuzzleInfoRead: bool
    lastUpdateTime: int
    solved: bool
    timeElapsed: int

    model_config = ConfigDict(extra="forbid")


class CrosswordGame(BaseModel):
    """Crossword Game."""
    status: str
    results: CrosswordGameResult

    model_config = ConfigDict(extra="forbid")


class CrosswordMiniCell(BaseModel):
    """Crossword Mini Cell."""
    answer: str | None = None
    clues: List[int] | None = None
    label: int | None = None
    type: int | None = None

    model_config = ConfigDict(extra="forbid")


class CrosswordMiniClue(BaseModel):
    """Crossword Mini Clue."""
    cells: List[int]
    direction: str
    label: str
    list: int | None = None
    relatives: List[int] | None = None
    text: List[Dict[str, str]]

    model_config = ConfigDict(extra="forbid")


class CrosswordMiniBodyClueList(BaseModel):
    """Crossword Mini Body Clue List."""
    clues: List[int]
    name: str

    model_config = ConfigDict(extra="forbid")


class CrosswordMiniBody(BaseModel):
    """Crossword Mini Body."""
    board: str
    cells: List[CrosswordMiniCell]
    clues: List[CrosswordMiniClue]
    clueLists: List[CrosswordMiniBodyClueList]
    dimensions: Dict[str, int]
    SVG: dict

    model_config = ConfigDict(extra="forbid")


class CrosswordMini(BaseModel):
    """Crossword Mini."""
    id: int
    body: List[CrosswordMiniBody]
    constructors: List[str]
    copyright: str
    editor: str
    freePuzzle: bool | None = None
    lastUpdated: str
    publicationDate: str
    subcategory: int

    model_config = ConfigDict(extra="forbid")


class CrosswordPublishType(str, Enum):
    """Crossword Publish Type."""
    daily = "daily"
    bonus = "bonus"
    mini = "mini"


class CrosswordPuzzleListItem(BaseModel):
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

    model_config = ConfigDict(extra="forbid")


class CrosswordPuzzlesList(BaseModel):
    """Crossword Puzzle List."""
    results: List[CrosswordPuzzleListItem]
    status: str

    model_config = ConfigDict(extra="forbid")


class CrosswordPuzzleRelatedContent(BaseModel):
    """Crossword Puzzle Related Content."""
    text: str
    url: str

    model_config = ConfigDict(extra="forbid")


class CrosswordPuzzleDataClue(BaseModel):
    """Crossword Puzzle Clue."""
    clueNum: int
    clueStart: int
    clueEnd: int
    formatted: str | None = None
    value: str

    model_config = ConfigDict(extra="forbid")


class CrosswordPuzzleData(BaseModel):
    """Crossword Puzzle Data."""
    answers: List[str | None]
    clues: Dict[str, List[CrosswordPuzzleDataClue]]
    clueListOrder: List[str]
    layout: List[int]

    model_config = ConfigDict(extra="forbid")


class CrosswordPuzzleMeta(BaseModel):
    """Crossword Puzzle Meta."""
    author: str
    copyright: str
    editor: str
    formatType: str
    height: int
    layoutExtra: list
    links: list
    notes: list
    printDate: str
    printDotw: int
    publishType: str
    title: str
    width: int

    relatedContent: CrosswordPuzzleRelatedContent

    model_config = ConfigDict(extra="forbid")


class CrosswordPuzzleResult(BaseModel):
    """Crossword Puzzle Result."""
    puzzle_id: int
    authors: List[str]
    enhanced_tier_date: None
    print_date: str
    promo_id: None
    puzzle_data: CrosswordPuzzleData
    puzzle_meta: CrosswordPuzzleMeta
    version: int

    model_config = ConfigDict(extra="forbid")


class CrosswordPuzzle(BaseModel):
    """Crossword Puzzle."""
    entitlement: str
    results: List[CrosswordPuzzleResult]
    status: str

    model_config = ConfigDict(extra="forbid")


class SpellingBeeGameDay(BaseModel):
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

    model_config = ConfigDict(extra="forbid")


class SpellingBeeGamePastPuzzles(BaseModel):
    """Spelling Bee Game Past Puzzles."""
    today: dict
    yesterday: dict
    lastWeek: list
    thisWeek: list

    model_config = ConfigDict(extra="forbid")


class SpellingBeeGameData(BaseModel):
    """Spelling Bee Game Data."""
    # today: SpellingBeeGameDay
    # yesterday: SpellingBeeGameDay
    pastPuzzles: SpellingBeeGamePastPuzzles

    # model_config = ConfigDict(extra="forbid")


class SpellingBeeLongestWord(BaseModel):
    """Spelling Bee Longest Word"""
    word: str
    center_letter: str
    print_date: str

    model_config = ConfigDict(extra="forbid")


class SpellingBeeRanks(BaseModel):
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

    model_config = ConfigDict(extra="forbid")


class SpellingBeeStatsSpellingBee(BaseModel):
    """Spelling Bee Stats - Spelling Bee."""
    puzzles_started: int
    total_words: int
    total_pangrams: int
    longest_word: SpellingBeeLongestWord
    ranks: SpellingBeeRanks

    model_config = ConfigDict(extra="forbid")


class SpellingBeeStatsWordleLegacyStatsGuesses(BaseModel):
    """Spelling Bee Stats - Wordle Legacy Stats Guesses."""
    one: int = Field(..., alias="1")
    two: int = Field(..., alias="2")
    three: int = Field(..., alias="3")
    four: int = Field(..., alias="4")
    five: int = Field(..., alias="5")
    six: int = Field(..., alias="6")
    fail: int

    model_config = ConfigDict(extra="forbid")


class SpellingBeeStatsWordleLegacyStats(BaseModel):
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

    model_config = ConfigDict(extra="forbid")


class SpellingBeeStatsWordle(BaseModel):
    """Spelling Bee Stats - Wordle"""
    legacyStats: SpellingBeeStatsWordleLegacyStats

    model_config = ConfigDict(extra="forbid")


class SpellingBeePlayerStats(BaseModel):
    """Spelling Bee Stats."""
    spelling_bee: SpellingBeeStatsSpellingBee
    wordle: SpellingBeeStatsWordle

    model_config = ConfigDict(extra="forbid")


class SpellingBeePlayer(BaseModel):
    """Spelling Bee Player."""
    user_id: int
    last_updated: int
    stats: SpellingBeePlayerStats

    model_config = ConfigDict(extra="forbid")


class SpellingBeeLatestStateGameData(BaseModel):
    """Spelling Bee Latest State Game Data."""
    answers: List[str]
    isRevealed: bool
    rank: str

    model_config = ConfigDict(extra="forbid")


class SpellingBeeLatestState(BaseModel):
    """Spelling Bee Latest State."""
    game_data: SpellingBeeLatestStateGameData
    game: str
    print_date: str
    puzzle_id: str
    schema_version: str
    timestamp: int
    user_id: int
    version: str

    model_config = ConfigDict(extra="forbid")


class SpellingBeeLatest(BaseModel):
    """Spelling Bee Latest."""
    user_id: int
    states: List[SpellingBeeLatestState]
    player: SpellingBeePlayer

    model_config = ConfigDict(extra="forbid")


class StrandsPuzzle(BaseModel):
    """Strands Puzzle."""
    id: int
    clue: str
    editor: str
    printDate: str
    solutions: List[str]
    spangram: str
    startingBoard: List[str]
    themeCoords: Dict[str, List[List[int]]]
    themeWords: List[str] | None = []

    model_config = ConfigDict(extra="forbid")


class WordlePuzzle(BaseModel):
    """Wordle Puzzle."""
    id: int
    days_since_launch: int
    editor: str
    print_date: str
    solution: str

    model_config = ConfigDict(extra="forbid")


class WordlePuzzlesList(BaseModel):
    """Wordle Puzzle List."""
    player: dict
    states: List[dict]
    user_id: int

    model_config = ConfigDict(extra="forbid")
