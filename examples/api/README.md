# Run your own NYT Games API

A minimal FastAPI app built on `nytgames.api`. Use it as a starting point for
your own `main.py` and container.

## Run locally

```bash
pip install "nytimes-games[api]"
uvicorn main:app --reload
```

Then open <http://localhost:8000/docs>.

## Run with Docker

```bash
docker build -t nyt-games-api .
docker run -p 8080:8080 nyt-games-api
```

Then open <http://localhost:8080/docs>.

## Cookies

Puzzles don't need cookies. Your stats and game progress need your `NYT-S`
cookie, which you can send with each request:

```bash
curl -H "Cookie: NYT-S=..." http://localhost:8080/player/stats
```

To use your own cookies for every request instead, set `NYT_COOKIES`:

```bash
docker run -p 8080:8080 -e NYT_COOKIES="NYT-S=..." nyt-games-api
```

Anyone who can reach the API can then see your stats and progress, so keep it
private.
