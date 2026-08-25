"""Tests for the generic raw_get_handler GET-fallback seam in the server."""
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

from skyhook.responses import RawGetResponse
from skyhook.server import Server


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"Server on port {port} did not start within {timeout}s")


class ServerContext:
    def __init__(self, port: int, **server_kwargs):
        self.port = port
        self._kwargs = server_kwargs
        self.server = None
        self._thread = None

    def __enter__(self):
        self.server = Server(port=self.port, echo_response=False, **self._kwargs)
        self._thread = threading.Thread(target=self.server.start_listening, daemon=True)
        self._thread.start()
        _wait_for_port(self.port)
        return self

    def __exit__(self, *_):
        if self.server is not None:
            self.server.stop_listening()
        if self._thread is not None:
            self._thread.join(timeout=3)


def test_raw_get_handler_serves_non_dispatch_get():
    calls = []

    def handler(path):
        calls.append(path)
        return RawGetResponse(b"hello raw", status=200, content_type="text/plain")

    port = _find_free_port()
    with ServerContext(port, raw_get_handler=handler) as ctx:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{ctx.port}/some/raw/path", timeout=5)
        assert resp.status == 200
        assert resp.headers.get("Content-type") == "text/plain"
        assert resp.read() == b"hello raw"
    assert calls == ["/some/raw/path"]


def test_dispatch_call_not_routed_to_raw_get_handler():
    calls = []

    def handler(path):
        calls.append(path)
        return RawGetResponse(b"should not happen", status=200)

    port = _find_free_port()
    with ServerContext(port, raw_get_handler=handler) as ctx:
        # A well-formed dispatch call for an unknown function still PARSES, so it
        # goes through dispatch (returns function_not_found JSON), never the seam.
        encoded = "/" + urllib.parse.quote('"nonexistent_fn"&{}', safe="")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{ctx.port}{encoded}", timeout=5)
        except Exception:
            pass
    assert calls == []


def test_raw_get_handler_none_falls_through():
    calls = []

    def handler(path):
        calls.append(path)
        return None

    port = _find_free_port()
    with ServerContext(port, raw_get_handler=handler) as ctx:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{ctx.port}/definitely/not/a/call", timeout=5)
        except Exception:
            pass
    assert calls == ["/definitely/not/a/call"]
