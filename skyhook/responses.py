from dataclasses import dataclass


@dataclass(frozen=True)
class HtmlResponse:
    """
    Sentinel class for handler functions that return HTML content.

    When a handler returns an HtmlResponse, the server will emit the body
    verbatim as HTML instead of encoding it as JSON.
    """
    body: str
    status: int = 200
    content_type: str = "text/html; charset=utf-8"


@dataclass(frozen=True)
class RawGetResponse:
    """
    A raw GET response produced by a Server.raw_get_handler.

    Lets an application serve arbitrary bytes (e.g. static files) for GET
    requests that are not Skyhook function-call dispatches. The body is bytes
    (unlike HtmlResponse.body, which is str) so any file type can be served.
    """
    body: bytes
    status: int = 200
    content_type: str = "application/octet-stream"
