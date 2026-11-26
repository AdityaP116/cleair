import logging
from typing import Optional
import redis
from app.config import settings

logger = logging.getLogger("cleair.redis")

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Return a shared Redis client with timeouts, or None if REDIS_URL is not configured."""
    global _redis_client
    if not settings.REDIS_URL:
        return None
    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
                retry_on_timeout=True,
                decode_responses=True,
            )
        except Exception as exc:
            logger.warning("Failed to initialize Redis client: %s", type(exc).__name__)
            _redis_client = None
    return _redis_client


def check_redis_health() -> bool:
    """Ping Redis to verify connectivity."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception as exc:
        logger.warning("Redis health check failed: %s", type(exc).__name__)
        return False
