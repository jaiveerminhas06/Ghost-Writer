"""A sliding-window rate limit per visitor. Endpoints call charge() with what the request costs.

Done as a function (not middleware) so a refusal is an ordinary ApiError: it passes through the CORS layer like any other
reply, and a batch can be charged by the number of files it holds, which a middleware cannot know before reading the body.
"""
import math
import time
from collections import defaultdict, deque

from fastapi import Request

from . import settings
from .errors import ApiError

_recent = defaultdict(deque)       # visitor -> deque of (time, cost)


def reset():
    _recent.clear()


def visitor(request: Request):
    # behind a host's proxy the real address is the first entry of X-Forwarded-For
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()


def charge(request: Request, cost=1.0):
    now, q = time.time(), _recent[visitor(request)]
    while q and now - q[0][0] > 60:
        q.popleft()
    if sum(c for _, c in q) + cost > settings.RATE_LIMIT_PER_MIN:
        wait = max(1, math.ceil(60 - (now - q[0][0]))) if q else 60
        raise ApiError(429, "rate_limited", f"Too many requests. Please wait {wait} seconds and try again.",
                       headers={"Retry-After": str(wait)})
    q.append((now, cost))
