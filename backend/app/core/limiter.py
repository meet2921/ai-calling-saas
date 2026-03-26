"""
Redis-backed rate limiter (slowapi).

Used on sensitive auth endpoints to block brute-force and abuse:
  - /login           5 / minute  per IP
  - /forgot-password 3 / minute  per IP
  - /reset-password  5 / minute  per IP
  - /refresh        10 / minute  per IP

Falls back to in-memory storage when REDIS_URL is not reachable
(e.g. unit tests) — slowapi handles this transparently.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=[],          # no global limit — per-route only
)
