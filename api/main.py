"""NYT Games API."""
import json
import re
from typing import Optional

import requests

from bs4 import BeautifulSoup

from fastapi import FastAPI
from fastapi import Path
from fastapi import Query

from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import StreamingResponse

from google.cloud import secretmanager

from altissimo.firestore import Firestore

from models import ConnectionsPuzzle
from models import CrosswordGame
from models import CrosswordMini
from models import CrosswordPublishType
from models import CrosswordPuzzle
from models import CrosswordPuzzlesList
from models import SpellingBeeGameData
from models import SpellingBeeLatest
from models import StrandsPuzzle
from models import WordlePuzzle
from models import WordlePuzzlesList


def get_game_data(body: bytes) -> dict | None:
    """Get Game Data from Spelling Bee Page."""
    soup = BeautifulSoup(body, 'html.parser')
    script_tag = soup.find('script', text=re.compile(r'window\.gameData\s*='))
    if script_tag:
        script_content = script_tag.string
        if script_content.startswith("window.gameData = {"):
            return json.loads(script_content[len("window.gameData = "):])
    return None


def get(url, request: Request, params=None) -> dict:
    """Return the response from a GET request."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    response = requests.get(
        url,
        cookies=request.cookies,
        headers=headers,
        params=params,
        timeout=30,
    )
    print(response.request.url)
    response.raise_for_status()
    return response.json()


app = FastAPI(
    contact={
        "name": "Lukas Karlsson",
        "email": "lukwam@gmail.com",
        "url": "https://github.com/lukwam",
    },
    description="NYT Games API built with FastAPI",
    openapi_tags=[
        {"name": "Connections", "description": "Connections Puzzles operations"},
        {"name": "Crosswords", "description": "Crossword Puzzles operations"},
        {"name": "Crosswords - Bonus", "description": "Crossword Bonus Puzzles operations"},
        {"name": "Crosswords - Daily", "description": "Crossword Daily Puzzles operations"},
        {"name": "Crosswords - Mini", "description": "Crossword Mini Puzzles operations"},
        {"name": "Spelling Bee", "description": "Spelling Bee Puzzles operations"},
        {"name": "Strands", "description": "Strands Puzzles operations"},
        {"name": "Wordle", "description": "Wordle Puzzles operations"},
    ],
    title="NYT Games API",
    version="0.0.1",
)


@app.middleware("http")
async def pretty_print_json_response(
    request: Request,
    call_next
) -> Response:
    """Pretty print JSON Response."""
    response = await call_next(request)

    # Paths to exclude from pretty printing
    excluded_paths = ["/docs", "/redoc", "/openapi.json"]

    # Skip excluded paths and non-streaming responses
    if request.url.path in excluded_paths or not isinstance(response, StreamingResponse):
        return response

    # Collect the stream into a single bytes object
    body = b""
    async for chunk in response.body_iterator:
        if isinstance(chunk, str):
            chunk = chunk.encode()  # Ensure chunk is bytes
        body += chunk

    # Only modify applicaton/json responses
    if response.headers.get('content-type') == 'application/json':
        data = json.loads(body.decode())
        pretty_json = json.dumps(
            data,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode("utf-8")

        # Create a new response with the pretty JSON and original status code
        response.headers["Content-Length"] = str(len(pretty_json))
        return Response(
            content=pretty_json,
            status_code=response.status_code,
            media_type="application/json",
            headers=dict(response.headers),
        )

    return response


# Connections
@app.get(
    "/connections/{date}",
    response_model=ConnectionsPuzzle,
    summary="Get the Connections puzzle for a specific date",
    tags=["Connections"],
)
async def get_connections_puzzle(
    request: Request,
    date: str = Path(..., example="2023-06-12"),
) -> ConnectionsPuzzle:
    """
    **Get a Connections puzzle**

    Returns the Connections puzzle for the date provided in the path parameter.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/connections/v2/{date}.json
    ```
    """
    response = get(
        f"https://www.nytimes.com/svc/connections/v2/{date}.json",
        request=request
    )
    return ConnectionsPuzzle(**response)


# Crosswords
@app.get(
    "/crosswords/game/{game_id}",
    response_model=CrosswordGame,
    summary="Get a Crossword Game",
    tags=["Crossword"],
)
async def get_crossword_game(
    request: Request,
    game_id: str = Path(..., example="1234"),
) -> CrosswordGame:
    """
    **Get a Crossword Game**

    Returns the Crossword Game for the date provided in the path parameter.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/crosswords/v2/game/{game_id}.json
    ```
    """
    response = get(
        f"https://www.nytimes.com/svc/crosswords/v2/game/{game_id}.json",
        request=request,
    )
    return CrosswordGame(**response)


# Crossword - Bonus
@app.get(
    "/crosswords/bonus/{date}",
    response_model=CrosswordPuzzle,
    summary="Get the Crossword Bonus puzzle for a specific date",
    tags=["Crosswords - Bonus"],
)
async def get_crossword_bonus(
    request: Request,
    date: str = Path(..., example="1997-02-01"),
):
    """
    **Get a Crossword Bonus puzzle**

    Returns the Crossword Bonus puzzle for the date provided in the path parameter.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/crosswords/v6/puzzle/bonus/{date}.json
    ```
    """
    return get(f"https://www.nytimes.com/svc/crosswords/v6/puzzle/bonus/{date}.json", request=request)


# Crossword - Daily
@app.get(
    "/crosswords/daily/today",
    response_model=CrosswordPuzzle,
    summary="Get the Crossword Daily puzzle for today",
    tags=["Crosswords - Daily"],
)
async def get_crossword_puzzle_daily(request: Request):
    """
    **Get the Crossword Daily puzzle for today**

    Returns the Crossword Daily puzzle for today.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/crosswords/v2/puzzle/daily.json
    ```
    """
    return get("https://www.nytimes.com/svc/crosswords/v2/puzzle/daily.json", request=request)


@app.get(
    "/crosswords/daily/{date}",
    response_model=CrosswordPuzzle,
    summary="Get the Crossword Daily puzzle for a specific date",
    tags=["Crosswords - Daily"])
async def get_crossword_puzzle(
    request: Request,
    date: str = Path(..., example="1993-11-21"),
) -> CrosswordPuzzle:
    """
    **Get a Crossword Daily puzzle**

    Returns the Crossword Daily puzzle for the date provided in the path parameter.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/crosswords/v2/puzzle/daily-{date}.json
    ```
    """
    response = get(
        f"https://www.nytimes.com/svc/crosswords/v2/puzzle/daily-{date}.json",
        request=request
    )
    return CrosswordPuzzle(**response)



# Crossword - Mini
@app.get("/crosswords/mini/today",
    response_model=CrosswordMini,
    summary="Get the Crossword Mini puzzle for today",
    tags=["Crosswords - Mini"])
async def get_crossword_mini_daily(request: Request) -> CrosswordMini:
    """
    **Get a Crossword Mini puzzle**

    Returns the Crossword Mini puzzle for today.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/crosswords/v6/puzzle/mini.json
    ```
    """
    return get("https://www.nytimes.com/svc/crosswords/v6/puzzle/mini.json")


@app.get("/crosswords/mini/{date}",
    response_model=CrosswordMini,
    summary="Get the Crossword Mini puzzle for a specific date",
    tags=["Crosswords - Mini"])
async def get_crossword_mini(
    request: Request,
    date: str = Path(..., example="2014-08-14"),
    ):
    """
    **Get a Crossword Mini puzzle**

    Returns the Crossword Mini puzzle for the date provided in the path parameter.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/crosswords/v6/puzzle/mini/{date}.json
    ```
    """
    return get(f"https://www.nytimes.com/svc/crosswords/v6/puzzle/mini/{date}.json", request=request)



@app.get("/crosswords/puzzles", response_model=CrosswordPuzzlesList, tags=["Crosswords"])
async def list_crossword_puzzles(
    request: Request,
    publish_type: Optional[CrosswordPublishType] = Query(None, example="daily"),
    sort_order: Optional[str] = Query(None, example="asc"),
    sort_by: Optional[str] = Query(None, example="print_date"),
    date_start: Optional[str] = Query(None, example="2024-07-01"),
    date_end: Optional[str] = Query(None, example="2024-07-31")
    ):
    """
    **List Crossword Puzzles**

    Returns a list of Crossword Puzzles bsaed on the url parameters.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/crosswords/v3/puzzles.json
    ```
    """
    params = {
        "publish_type": publish_type,
        "sort_order": sort_order,
        "sort_by": sort_by,
        "date_start": date_start,
        "date_end": date_end,
    }
    return get("https://www.nytimes.com/svc/crosswords/v3/puzzles.json", params=params,request=request)



# pylint: disable=line-too-long,too-many-arguments
# @app.get("/crosswords/{user_id}/puzzles.json", response_model=CrosswordPuzzlesList, tags=["Crossword"])
# async def list_user_crossword_puzzles(
#     user_id,
#     publish_type: str = Query(default="daily"),
#     sort_order: str = Query(default="asc"),
#     sort_by: str = Query(default="print_date"),
#     date_start: str = Query(default="2024-01-01"),
#     date_end: str = Query(default="2024-12-31"),
# ):
#     """List Crossword Puzzles."""
#     params = {
#         "publish_type": publish_type,
#         "sort_order": sort_order,
#         "sort_by": sort_by,
#         "date_start": date_start,
#         "date_end": date_end,
#     }
#     url = f"https://www.nytimes.com/svc/crosswords/v3/{user_id}/puzzles.json"
#     response = requests.get(url, params=params, timeout=10)
#     response.raise_for_status()
#     return response.json()


# Spelling Bee
@app.get("/spelling-bee",
    response_model=SpellingBeeGameData,
    summary="Get current Spelling Bee data",
    tags=["Spelling Bee"])
async def get_spelling_bee(
    request: Request,
    ) -> SpellingBeeGameData:
    """
    **Get Current Spelling Bee Data**

    Returns a list of Spelling Bee puzzles based on the url parameters.

    **Backend API**
    ```
    GET https://www.nytimes.com/puzzles/spelling-bee
    ```
    """
    url = f"https://www.nytimes.com/puzzles/spelling-bee"
    response = requests.get(
        url,
        cookies=request.cookies,
        timeout=30,
    )
    print(response.request.url)
    response.raise_for_status()
    return get_game_data(response.content)


@app.get("/spelling-bee/latest",
    response_model=SpellingBeeLatest,
    summary="List latest Spelling Bee puzzles",
    tags=["Spelling Bee"])
async def get_spelling_bee_latest(
    request: Request,
    puzzle_ids: str = Query(None, example="1,2,3,4,5,6,7"),
    ) -> WordlePuzzlesList:
    """
    **List latest Spelling Bee puzzles**

    Returns a list of Spelling Bee puzzles based on the url parameters.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/games/state/spelling_bee/latests"
    ```
    """
    url = f"https://www.nytimes.com/svc/games/state/spelling_bee/latests"
    if puzzle_ids:
        url = f"{url}?puzzle_ids={puzzle_ids}"
    return get(url, request=request)


# Strands
@app.get("/strands/{date}",
    response_model=StrandsPuzzle,
    summary="Get the Strands puzzle for a specific date",
    tags=["Strands"])
async def get_strands_puzzle(
    request: Request,
    date: str = Path(..., example="2024-03-04"),
    ):
    """
    **Get a Strands puzzle**

    Returns the Strands puzzle for the date provided in the path parameter.

    **Backend API**
    ```
    GET https://www.nytimes.com/games-assets/strands/{date}.json
    ```
    """
    return get(f"https://www.nytimes.com/games-assets/strands/{date}.json", request=request)


# Wordle
@app.get("/wordle/latest",
    response_model=WordlePuzzlesList,
    summary="List latest Wordle puzzles",
    tags=["Wordle"])
async def list_latest_wordle_puzzles(
    request: Request,
    puzzle_ids: str = Query(None, example="1,2,3,4,5,6,7"),
    ) -> WordlePuzzlesList:
    """
    **List latest Wordle puzzles**

    Returns a list of Wordle puzzles based on the url parameters.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/games/state/wordleV2/latests
    ```
    """
    url = f"https://www.nytimes.com/svc/games/state/wordleV2/latests"
    if puzzle_ids:
        url = f"{url}?puzzle_ids={puzzle_ids}"
    return get(url, request=request)



@app.get("/wordle/{date}",
    response_model=WordlePuzzle,
    summary="Get the Wordle puzzle for a specific date",
    tags=["Wordle"])
async def get_wordle_puzzle(
    request: Request,
    date: str = Path(..., example="2021-06-19"),
    ):
    """
    **Get a Wordle puzzle**

    Returns the Wordle puzzle for the date provided in the path parameter.

    **Backend API**
    ```
    GET https://www.nytimes.com/svc/wordle/v2/{date}.json
    ```
    """
    return get(f"https://www.nytimes.com/svc/wordle/v2/{date}.json", request=request)
