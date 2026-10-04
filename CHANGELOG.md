# Changelog

All notable changes to this project. The project follows
[Semantic Versioning](https://semver.org/); while it's below 1.0, minor
versions may include breaking changes.

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
