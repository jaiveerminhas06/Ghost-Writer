"""Keeping uploaded essays off the disk.

The page says "Scores are kept on this computer and cleared when you close the tab", so an uploaded file must never be saved by
the server. Two things make that true:

1. Starlette (the web framework under FastAPI) keeps each uploaded file in a "spooled" temporary file: in memory up to a size
   (1 MB by default) and written to a file in /tmp above it. We raise that size above anything we accept, so no file part can
   reach the disk.
2. A request larger than MAX_REQUEST_BYTES is refused before it is read: first by its Content-Length header, and, for a
   request that does not declare one, as soon as the bytes counted while it streams in pass the limit.

tests/test_privacy.py checks both (a 3 MB upload stays in memory; an oversized one is refused; nothing appears in the temp
folder; the essay text is not in the logs).
"""
from starlette.formparsers import MultiPartParser
from starlette.responses import JSONResponse

from . import settings
from .errors import ApiError

# every part of an accepted request is smaller than this, so no SpooledTemporaryFile ever rolls over to disk
MultiPartParser.spool_max_size = settings.MAX_REQUEST_BYTES + 1

_TOO_LARGE = "This upload is larger than {mb} MB. Send fewer or smaller files."


def _message():
    return _TOO_LARGE.format(mb=settings.MAX_REQUEST_BYTES // (1024 * 1024))


class BodyLimit:
    """ASGI middleware: refuse a request body larger than settings.MAX_REQUEST_BYTES (read at call time, so tests can change it)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        limit = settings.MAX_REQUEST_BYTES
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            return await JSONResponse({"detail": _message(), "code": "too_large"}, status_code=413)(scope, receive, send)
        seen = 0

        async def counted():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:
                    raise ApiError(413, "too_large", _message())      # answered by the app's ApiError handler
            return message

        await self.app(scope, counted, send)
