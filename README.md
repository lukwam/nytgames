# nytimes-games

[![PyPI](https://img.shields.io/pypi/v/nytimes-games)](https://pypi.org/project/nytimes-games/)
[![Python](https://img.shields.io/pypi/pyversions/nytimes-games)](https://pypi.org/project/nytimes-games/)
[![Test](https://github.com/lukwam/nytgames/actions/workflows/test.yml/badge.svg)](https://github.com/lukwam/nytgames/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lukwam/nytgames/blob/main/LICENSE)

Unofficial Python client and API for the New York Times Games APIs (Wordle,
Connections, Strands, Spelling Bee, Letter Boxed and the Daily, Mini, Midi and
Bonus crosswords). Responses are validated with Pydantic models.

This repo contains:

- `nytgames/`: the Python library, published on PyPI as `nytimes-games`
- `api/`: a FastAPI service built on the library, deployed to Cloud Run

Puzzles are available without logging in. Your game progress and stats require
your NYT session cookie (`NYT-S`) from a logged in nytimes.com browser session.

## Library

```bash
pip install nytimes-games
```

The package installs as `nytimes-games` and is imported as `nytgames`.

```python
from nytgames import NYTGamesClient, spelling_bee_hints

client = NYTGamesClient(cookies="NYT-S=...")

client.wordle("2025-06-12").solution
client.connections("2025-06-12").categories
client.letter_boxed("2026-10-03").sides
client.crossword()                        # today's daily crossword
client.crossword("mini", "2025-06-12")    # daily, mini, midi or bonus
client.crossword_oracle("midi")           # current and next puzzle IDs
client.crossword_game(24287)              # your saved progress on a puzzle
client.crossword_puzzles("daily", date_start="2025-06-01", date_end="2025-06-30")
client.player_stats().stats.connections.current_streak   # your stats for every game

puzzle = client.spelling_bee_puzzle("2026-10-03")   # any date from 2018-05-06
spelling_bee_hints(puzzle)                          # Spelling Bee Forum style hints
client.spelling_bee_puzzles()   # {print_date: puzzle} from the game page, about two weeks
```

`cookies` can be a dict, a `Cookie` header string, or a list of cookie objects
with `name` and `value` keys, such as a JSON export from the Cookie-Editor
browser extension.

HTTP errors from NYT are raised as `NYTGamesHTTPError`, a subclass of
`requests.HTTPError`: `NYTGamesAuthenticationError` for 401 and 403 (usually a
missing or expired `NYT-S` cookie) and `NYTGamesNotFoundError` for 404 (e.g. a
date with no puzzle).

## API

Each endpoint calls NYT with the cookies sent to the API:

```bash
curl -H "Cookie: NYT-S=..." http://localhost:8080/crosswords/mini/today
```

Interactive docs are served at `/docs` and `/redoc`.

### Endpoints

| Route | Upstream NYT endpoint |
|---|---|
| `GET /connections/{date}` | `svc/connections/v2/{date}.json` |
| `GET /crosswords/daily/today` | `svc/crosswords/v6/puzzle/daily.json` |
| `GET /crosswords/daily/{date}` | `svc/crosswords/v6/puzzle/daily/{date}.json` |
| `GET /crosswords/mini/today` | `svc/crosswords/v6/puzzle/mini.json` |
| `GET /crosswords/mini/{date}` | `svc/crosswords/v6/puzzle/mini/{date}.json` |
| `GET /crosswords/bonus/{date}` | `svc/crosswords/v6/puzzle/bonus/{date}.json` |
| `GET /crosswords/puzzles` | `svc/crosswords/v3/puzzles.json` |
| `GET /crosswords/midi/today` | `svc/crosswords/v6/puzzle/midi.json` |
| `GET /crosswords/midi/{date}` | `svc/crosswords/v6/puzzle/midi/{date}.json` |
| `GET /crosswords/oracle/{publish_type}` | `svc/crosswords/v2/oracle/{publish_type}.json` (current and next puzzle; `daily`, `midi`, `mini`) |
| `GET /crosswords/game/{game_id}?publish_type=daily` | `svc/games/state/crossword_{publish_type}/latests?puzzle_ids={game_id}` (your saved progress) |
| `GET /letter-boxed/{date}` | `svc/letter-boxed/v1/{date}.json` |
| `GET /player/stats` | `svc/games/state/wordleV2/latests?puzzle_ids=0` (your stats for every game) |
| `GET /spelling-bee` | Scraped from `puzzles/spelling-bee` |
| `GET /spelling-bee/latest` | `svc/games/state/spelling_bee/latests` (up to 30 `puzzle_ids`) |
| `GET /spelling-bee/{date}` | `svc/spelling-bee/v1/{date}.json` (from 2018-05-06) |
| `GET /spelling-bee/{date}/hints` | Computed from the puzzle above |
| `GET /strands/{date}` | `svc/strands/v2/{date}.json` |
| `GET /wordle/latest` | `svc/games/state/wordleV2/latests` |
| `GET /wordle/{date}` | `svc/wordle/v2/{date}.json` |

Upstream errors (e.g. a 404 for a date with no puzzle) are returned with the
upstream status code.

## Development

```bash
pip install -e ".[api,test]"
pytest
cd api && uvicorn main:app --reload --port 8080
```

`api/build.sh` builds the image locally. `api/develop.sh` runs the deployed
image with the repo mounted and auto-reload enabled.

## Deployment

`api/cloudbuild.yaml` builds the image, pushes it to Artifact Registry
(`us-central1-docker.pkg.dev/$PROJECT_ID/docker/nytgames`) tagged `latest` and
`$SHORT_SHA`, and deploys it to the `nytgames` Cloud Run service in
`us-central1`.

## License

MIT. This project is not affiliated with The New York Times.
