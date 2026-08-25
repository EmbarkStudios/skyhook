"""
Tests for HtmlResponse and the server's HTML dispatch path.
"""
import json
import socket
import threading
import types
import urllib.error
import urllib.parse
import urllib.request

import pytest

from skyhook.responses import HtmlResponse
from skyhook.server import Server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    """Ask the OS for a free port then immediately release it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(port: int, function_name: str, params: dict | None = None) -> urllib.request.Request:
    """Return a urllib response for a GET call to the skyhook server."""
    if params is None:
        params = {}
    # URL format: /"function_name"&{"key": "value"}
    path = f'"{function_name}"&{json.dumps(params)}'
    encoded = urllib.parse.quote(path)
    url = f"http://127.0.0.1:{port}/{encoded}"
    return urllib.request.urlopen(url, timeout=5)


class ServerContext:
    """
    Spin up a Server instance in a daemon thread; tear it down afterwards.

    Usage::

        with ServerContext(port, static_dir=...) as ctx:
            response = _get(ctx.port, "my_func")
    """

    def __init__(self, port: int, **server_kwargs):
        self.port = port
        self._server_kwargs = server_kwargs
        self.server: Server | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "ServerContext":
        self.server = Server(port=self.port, echo_response=False, **self._server_kwargs)
        self._thread = threading.Thread(target=self.server.start_listening, daemon=True)
        self._thread.start()
        # Give the server a moment to bind
        _wait_for_port(self.port)
        return self

    def __exit__(self, *_):
        if self.server is not None:
            self.server.stop_listening()
        if self._thread is not None:
            self._thread.join(timeout=3)


def _wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 5.0) -> None:
    """Block until the port is accepting connections, or raise TimeoutError."""
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"Server on port {port} did not start within {timeout}s")


# ---------------------------------------------------------------------------
# HtmlResponse unit tests (no server needed)
# ---------------------------------------------------------------------------

class TestHtmlResponseDefaults:
    def test_status_default(self):
        r = HtmlResponse(body="<p>hi</p>")
        assert r.status == 200

    def test_content_type_default(self):
        r = HtmlResponse(body="<p>hi</p>")
        assert r.content_type == "text/html; charset=utf-8"

    def test_body_stored(self):
        r = HtmlResponse(body="<h1>Hello</h1>")
        assert r.body == "<h1>Hello</h1>"


class TestHtmlResponseCustomValues:
    def test_custom_status(self):
        r = HtmlResponse(body="not found", status=404)
        assert r.status == 404

    def test_custom_content_type(self):
        r = HtmlResponse(body="data", content_type="text/plain; charset=utf-8")
        assert r.content_type == "text/plain; charset=utf-8"


class TestHtmlResponseFrozen:
    def test_frozen_body(self):
        from dataclasses import FrozenInstanceError
        r = HtmlResponse(body="<p>x</p>")
        with pytest.raises(FrozenInstanceError):
            r.body = "changed"

    def test_frozen_status(self):
        from dataclasses import FrozenInstanceError
        r = HtmlResponse(body="<p>x</p>")
        with pytest.raises(FrozenInstanceError):
            r.status = 500

    def test_frozen_content_type(self):
        from dataclasses import FrozenInstanceError
        r = HtmlResponse(body="<p>x</p>")
        with pytest.raises(FrozenInstanceError):
            r.content_type = "text/plain"


# ---------------------------------------------------------------------------
# Integration tests — HtmlResponse dispatch path
# ---------------------------------------------------------------------------

class TestHtmlDispatch:
    """Spin up a real server and make real HTTP requests."""

    def _make_server_with_html_handler(self):
        """Return (port, module) ready for ServerContext."""
        port = _find_free_port()
        mod = types.ModuleType("_test_html_mod")

        def my_html_handler():
            return HtmlResponse(body="<h1>Hello</h1>", status=200)

        mod.my_html_handler = my_html_handler
        return port, mod

    def test_content_type_header(self):
        port, mod = self._make_server_with_html_handler()
        with ServerContext(port) as ctx:
            ctx.server.hotload_module(mod, is_skyhook_module=False)
            resp = _get(ctx.port, "my_html_handler")
            ct = resp.headers.get("Content-type", "")
            assert ct == "text/html; charset=utf-8"

    def test_body_is_verbatim_html(self):
        port, mod = self._make_server_with_html_handler()
        with ServerContext(port) as ctx:
            ctx.server.hotload_module(mod, is_skyhook_module=False)
            resp = _get(ctx.port, "my_html_handler")
            body = resp.read().decode("utf-8")
            assert "<h1>Hello</h1>" in body

    def test_no_window_close_script(self):
        port, mod = self._make_server_with_html_handler()
        with ServerContext(port) as ctx:
            ctx.server.hotload_module(mod, is_skyhook_module=False)
            resp = _get(ctx.port, "my_html_handler")
            body = resp.read().decode("utf-8")
            assert "window.close()" not in body
            assert "window.open" not in body

    def test_http_status_matches_html_response(self):
        port = _find_free_port()
        mod = types.ModuleType("_test_html_404_mod")

        def page_not_found():
            return HtmlResponse(body="<p>Not found</p>", status=404)

        mod.page_not_found = page_not_found

        with ServerContext(port) as ctx:
            ctx.server.hotload_module(mod, is_skyhook_module=False)
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                _get(ctx.port, "page_not_found")
            assert exc_info.value.code == 404

    def test_body_not_json_wrapped(self):
        """The body must be raw HTML, not a JSON envelope."""
        port, mod = self._make_server_with_html_handler()
        with ServerContext(port) as ctx:
            ctx.server.hotload_module(mod, is_skyhook_module=False)
            resp = _get(ctx.port, "my_html_handler")
            body = resp.read().decode("utf-8")
            # Must NOT start with a JSON object
            assert not body.strip().startswith("{")
            assert not body.strip().startswith('"')


# ---------------------------------------------------------------------------
# Regression: plain-dict handlers still return JSON
# ---------------------------------------------------------------------------

class TestDictHandlerReturnsJson:
    def test_dict_handler_is_json(self):
        port = _find_free_port()
        mod = types.ModuleType("_test_dict_mod")

        def echo_handler():
            return {"msg": "hello"}

        mod.echo_handler = echo_handler

        with ServerContext(port) as ctx:
            ctx.server.hotload_module(mod, is_skyhook_module=False)
            resp = _get(ctx.port, "echo_handler")
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            # The server wraps the return value in a result envelope
            assert data["Success"] is True
            assert data["ReturnValue"] == {"msg": "hello"}
