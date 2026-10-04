# Changelog

All notable changes to this project. The project follows
[Semantic Versioning](https://semver.org/); while it's below 1.0, minor
versions may include breaking changes.

## Unreleased

### Added

- A live check of every game against NYT runs every morning, with a README
  badge showing the latest result. Failures open an issue automatically.
- A coverage badge.
- Puzzle structure helpers: `CrosswordPuzzle.entries()` (each entry's clue,
  full answer, squares, coordinates, crossings and referenced clues) and
  `.squares()`, `StrandsPuzzle.words()` (words with their paths) and
  `ConnectionsPuzzle.board()`. Special puzzles are kept as they are.

- Retries with exponential backoff for failed connections, timeouts, rate
  limits and NYT server errors, honoring `Retry-After`
  (`NYTGamesClient(retries=3, backoff=0.5)`). Sessions you pass in are used
  as is.
- `NYTGamesRateLimitError` (429 after retries) with `retry_after`, and a
  matching nytg message.
- `NYTGamesClient(base_url=...)`, for proxies and testing.
- `urllib3` is declared as a dependency (it comes with requests).

### Fixed

- `crossword_puzzles()` returned a validation error when NYT sends null
  results (for empty ranges and ranges that are too long); it now returns an
  empty list. Its docs recommend ranges of 90 days or less.

## 0.7.0

### Added

- `nytgames.formats`: export crosswords to Across Lite `.puz`, `.ipuz` and
  Crossword Compiler rectangular-puzzle `.xml`, with the user's saved
  progress (fill, revealed and penciled squares, and the .puz timer).
  Rebus squares, circles and shading are kept where the format allows.
  `export()`, `to_puz()`, `to_ipuz()`, `to_xml()` and `export_problems()`.
- `NYTGamesExportError` for puzzles whose gimmicks a format can't represent,
  with the reasons.
- `nytg crossword ... --save FILE [--progress]` and
  `nytg archive crossword-* --as puz|ipuz|xml`.
- API route `/crosswords/{publish_type}/{date}/download?format=puz`.

## 0.6.1

### Fixed

- Crosswords with special square labels no longer fail validation.
  `CrosswordPuzzleCell.label` is still an int for numbered squares, and a
  string for text labels such as `CW` or arrows (2000-02-13, 2007-07-01,
  2017-07-02). `CrosswordPuzzleClue.label` is optional, for special clues
  like 2016-03-24's "Around" clue.
- `nytg crossword --answers` no longer repeats letters in clues that turn a
  corner.

## 0.6.0

### Added

- `nytgames.cli.extension`: a public API for building command lines on top
  of nytg. `create_app(name=, help=, version=)` returns an independent Typer
  app with every nytg command and root option, and `run(app)` runs it with
  nytg's error messages and exit codes. `emit()`, `FormatOption`,
  `get_client()`, `resolve_cookies()`, `active_profile()`, `get_setting()`,
  `parse_date()`, `key_value_table()` and the Rich consoles help extension
  commands behave like nytg's. `create_app` and `run` are also importable
  from `nytgames.cli`.

### Changed

- Error messages name the running command, for example `mytool auth login`.

## 0.5.0

### Added

- `nytg`, a command line tool, behind the `cli` extra
  (`pip install "nytimes-games[cli]"`): puzzles for every game with answers
  hidden unless `--answers`, Spelling Bee hints, crossword grids and clues,
  `stats`, `today`, `history` (crossword, Wordle, Spelling Bee), resumable
  `archive`, gcloud-style `--format` (table, json, yaml, csv, value()),
  `auth login`, and settings and profiles in `~/.config/nytg/config.ini`.
- `archive(game, date_start, date_end)`: the puzzles published in a date
  range, with their IDs, for Wordle, Connections, Strands and the Daily, Mini
  and Midi crosswords, from NYT's games archive. Ranges longer than 31 days
  are split automatically. Also served by the API at
  `/archive/{game}/{date_start}/{date_end}`.
- `crossword_game()`, `wordle_latest()` and `spelling_bee_latest()` accept a
  list of puzzle IDs.

- Python 3.14 support. Python 3.15 is tested while it's in pre-release.

### Fixed

- `crossword_puzzles("midi")` raises `ValueError` instead of returning Daily
  puzzles, which is what NYT's list returns for Midi; use `archive()` for
  Midi puzzles. The API returns 400.

## 0.4.0

### Added

- `nytgames.api`: the REST API is now part of the package, behind the `api`
  extra (`pip install "nytimes-games[api]"`). Run it with
  `uvicorn nytgames.api:app`, customize it with `create_app()`, or mount
  `router` in your own FastAPI app with `add_exception_handlers()`. Override
  the `get_client` dependency to use your own cookies.
- `examples/api`: an example `main.py` and `Dockerfile` for running your own
  instance.
- `NYTGamesParseError` responses from the API return 502 instead of 500.

### Changed

- The package source moved to `src/nytgames` (src layout). Imports are
  unchanged.
- The API no longer pretty-prints JSON responses and no longer configures
  logging.

### Removed

- The standalone `api/` service and its deployment files.

## 0.3.2

### Fixed

- Connections picture puzzles, whose cards have `image_url` and
  `image_alt_text` instead of `content`. Added `card.text` and
  `ConnectionsPuzzle.illustrator`.

## 0.3.1

- First release on PyPI, as `nytimes-games`. Ships `py.typed`.

## 0.3.0

### Added

- `spelling_bee_puzzle(date)`: any Spelling Bee from 2018-05-06.

## 0.2.1

- Corrected the documented Letter Boxed date range.

## 0.2.0

### Added

- `letter_boxed(date)`.
- `player_stats()`: your stats for every game.
- Typed errors: `NYTGamesHTTPError`, `NYTGamesAuthenticationError`,
  `NYTGamesNotFoundError`, `NYTGamesParseError`.
- A `nytimes-games` User-Agent.

## 0.1.0

- First release as an installable library, with endpoints updated for NYT's
  current APIs.
