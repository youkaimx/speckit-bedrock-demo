"""Per-user rate limiter middleware (FR-013): throttle by owner_id; return 429 when exceeded."""

import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.config import get_settings


class InMemoryRateLimiter:
    """In-memory per-user rate limit. For production use Redis or similar."""

    def __init__(self, requests: int, window_seconds: int):
        self.requests = requests
        self.window_seconds = window_seconds
        self._counts: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        self._counts[key] = [t for t in self._counts[key] if t > window_start]
        if len(self._counts[key]) >= self.requests:
            return False
        self._counts[key].append(now)
        return True


_limiter: InMemoryRateLimiter | None = None


def get_limiter() -> InMemoryRateLimiter:
    global _limiter
    if _limiter is None:
        s = get_settings()
        _limiter = InMemoryRateLimiter(
            requests=s.rate_limit_requests,
            window_seconds=s.rate_limit_window_seconds,
        )
    return _limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that returns 429 when per-user rate limit is exceeded."""

    async def dispatch(self, request: Request, call_next):
        # owner_id is set by auth dependency on protected routes; we need it from state or header
        owner_id = getattr(request.state, "owner_id", None)
        if not owner_id:
            # Let the route handle 401; we only rate-limit when we have a user
            return await call_next(request)
        limiter = get_limiter()
        if not limiter.is_allowed(owner_id):
            return Response(
                content='{"error": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
        return await call_next(request)


def set_request_owner(request: Request, owner_id: str) -> None:
    """Set owner_id on request.state for rate limit middleware."""
    request.state.owner_id = owner_id
