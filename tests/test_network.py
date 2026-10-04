"""Retry and rate limit tests against a local HTTP server."""
import json
import threading
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

import pytest
import requests

from nytgames import NYTGamesClient
from nytgames import NYTGamesHTTPError
from nytgames import NYTGamesRateLimitError

WORDLE = {"id": 1, "print_date": "2025-06-12", "solution": "vixen"}


@pytest.fixture
def server():
    """A server that answers with the queued (status, headers) responses, then 200."""
    queue = []
    requests_seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            requests_seen.append(self.path)
            status, headers = queue.pop(0) if queue else (200, {})
            body = json.dumps(WORDLE).encode() if status == 200 else b"{}"
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", queue, requests_seen
    httpd.shutdown()


def client(base_url, **kwargs):
    return NYTGamesClient(base_url=base_url, backoff=0, **kwargs)


def test_server_errors_and_rate_limits_are_retried(server):
    base_url, queue, seen = server
    queue.extend([(503, {}), (429, {"Retry-After": "0"}), (502, {})])
    assert client(base_url).wordle("2025-06-12").solution == "vixen"
    assert len(seen) == 4


def test_rate_limit_error_after_retries(server):
    base_url, queue, seen = server
    queue.extend([(429, {"Retry-After": "0"})] * 3)
    with pytest.raises(NYTGamesRateLimitError) as info:
        client(base_url, retries=2).wordle("2025-06-12")
    assert info.value.response.status_code == 429
    assert info.value.retry_after == 0
    assert isinstance(info.value, NYTGamesHTTPError) and isinstance(info.value, requests.HTTPError)
    assert len(seen) == 3


def test_client_errors_are_not_retried(server):
    base_url, queue, seen = server
    queue.append((404, {}))
    with pytest.raises(NYTGamesHTTPError):
        client(base_url).wordle("1900-01-01")
    assert len(seen) == 1


def test_retries_can_be_turned_off(server):
    base_url, queue, seen = server
    queue.append((503, {}))
    with pytest.raises(NYTGamesHTTPError):
        client(base_url, retries=0).wordle("2025-06-12")
    assert len(seen) == 1


def test_your_own_session_is_used_as_is():
    session = requests.Session()
    assert NYTGamesClient(session=session).session is session
    assert session.adapters["https://"].max_retries.total == 0


def test_connection_errors_are_retried_then_raised():
    with pytest.raises(requests.ConnectionError):
        NYTGamesClient(base_url="http://127.0.0.1:9", backoff=0, retries=1, timeout=2).wordle("2025-06-12")
