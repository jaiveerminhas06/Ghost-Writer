"""One error shape for the whole API: {"detail": "<a sentence the page can show as it is>", "code": "<machine name>"}."""
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    """An HTTP error with a machine-readable `code`. It is an HTTPException on purpose: FastAPI turns any other exception raised
    while it reads a request body into a generic 400, but lets an HTTPException through, so a 413 for an oversized body stays a 413."""

    def __init__(self, status, code, detail, headers=None):
        super().__init__(status_code=status, detail=detail, headers=headers or {})
        self.status, self.code = status, code


async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse({"detail": exc.detail, "code": exc.code}, status_code=exc.status, headers=exc.headers)


async def validation_handler(request: Request, exc: RequestValidationError):
    # pydantic's own messages are for programmers; the page gets one plain sentence
    where = ".".join(str(p) for p in exc.errors()[0]["loc"][1:]) if exc.errors() else "request"
    return JSONResponse({"detail": f"The request was not understood ({where}).", "code": "bad_request"}, status_code=422)
