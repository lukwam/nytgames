# nytgames

Unofficial NYT Games API built with FastAPI. Each endpoint proxies an internal
`nytimes.com` endpoint and validates the response with Pydantic models.

Requests are made with the cookies sent to this API, so pass your NYT session
cookie (`NYT-S`) to get subscriber and user-specific data:

```bash
curl -H "Cookie: NYT-S=..." http://localhost:8080/crosswords/mini/today
```

Interactive docs are served at `/docs` and `/redoc`.

## Endpoints

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
| `GET /spelling-bee` | Scraped from `puzzles/spelling-bee` |
| `GET /spelling-bee/latest` | `svc/games/state/spelling_bee/latests` |
| `GET /strands/{date}` | `svc/strands/v2/{date}.json` |
| `GET /wordle/latest` | `svc/games/state/wordleV2/latests` |
| `GET /wordle/{date}` | `svc/wordle/v2/{date}.json` |

Upstream errors (e.g. a 404 for a date with no puzzle) are returned with the
upstream status code.

## Development

```bash
cd api
pip install -r requirements.txt pytest
uvicorn main:app --reload --port 8080
pytest main_tests.py
```

`api/develop.sh` runs the deployed image locally with the current directory
mounted and auto-reload enabled. `api/build.sh` builds the image locally.

## Deployment

`api/cloudbuild.yaml` builds the image, pushes it to Artifact Registry
(`us-central1-docker.pkg.dev/$PROJECT_ID/docker/nytgames`) tagged `latest` and
`$SHORT_SHA`, and deploys it to the `nytgames` Cloud Run service in
`us-central1`.
