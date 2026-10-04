"""Run your own NYT Games API.

    pip install "nytimes-games[api]"
    uvicorn main:app --reload

By default each request is made with the cookies sent to your API. Set
NYT_COOKIES (for example "NYT-S=...") to use your own cookies for every
request instead, and keep the API private if you do.
"""
import os

from nytgames import NYTGamesClient
from nytgames.api import create_app
from nytgames.api import get_client

app = create_app(title="My NYT Games API")

if cookies := os.environ.get("NYT_COOKIES"):
    app.dependency_overrides[get_client] = lambda: NYTGamesClient(cookies=cookies)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    """Health check for your load balancer or container platform."""
    return {"status": "ok"}
