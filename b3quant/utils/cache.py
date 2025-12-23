"""Cache utilities with Time-To-Live (TTL) support"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


class CacheBackend:
    """Abstract base class for cache backends"""

    def get(self, key: str) -> Any | None:
        """Get value from cache by key"""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL (seconds)"""
        raise NotImplementedError

    def delete(self, key: str) -> None:
        """Delete key from cache"""
        raise NotImplementedError

    def clear(self) -> None:
        """Clear all cache entries"""
        raise NotImplementedError

    def cleanup_expired(self) -> int:
        """Remove expired entries, return count deleted"""
        raise NotImplementedError


class JSONCache(CacheBackend):
    """
    JSON-based cache with TTL support.

    Stores cache entries in a JSON file with expiration timestamps.
    Lightweight and human-readable, suitable for small to medium datasets.

    Examples:
        >>> cache = JSONCache(cache_dir="./cache")
        >>> cache.set("key1", {"data": "value"}, ttl=3600)  # Expires in 1 hour
        >>> value = cache.get("key1")
        >>> cache.cleanup_expired()  # Remove expired entries
    """

    def __init__(self, cache_dir: str | Path = "./data/cache"):
        """
        Initialize JSON cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "cache.json"
        self._cache: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load cache from JSON file"""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                return json.load(f)  # type: ignore[no-any-return]
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                f"Failed to load cache file: {e}. Starting with empty cache."
            )
            return {}

    def _save(self) -> None:
        """Save cache to JSON file"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save cache file: {e}")

    def get(self, key: str) -> Any | None:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        expires_at = entry.get("expires_at")

        # Check if expired
        if expires_at and time.time() > expires_at:
            logger.debug(f"Cache key '{key}' has expired")
            self.delete(key)
            return None

        logger.debug(f"Cache hit for key '{key}'")
        return entry.get("value")

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (None = never expires)
        """
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl

        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": time.time(),
        }

        self._save()
        logger.debug(f"Cache set for key '{key}' (TTL: {ttl}s)")

    def delete(self, key: str) -> None:
        """Delete entry from cache"""
        if key in self._cache:
            del self._cache[key]
            self._save()
            logger.debug(f"Cache key '{key}' deleted")

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache = {}
        self._save()
        logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries deleted
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if entry.get("expires_at") and current_time > entry["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self._save()
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)


class SQLiteCache(CacheBackend):
    """
    SQLite-based cache with TTL support.

    Stores cache entries in a SQLite database with automatic indexing.
    More efficient for large datasets and concurrent access.

    Examples:
        >>> cache = SQLiteCache(cache_dir="./cache")
        >>> cache.set("key1", {"data": "value"}, ttl=3600)
        >>> value = cache.get("key1")
        >>> cache.cleanup_expired()
    """

    def __init__(self, cache_dir: str | Path = "./data/cache"):
        """
        Initialize SQLite cache.

        Args:
            cache_dir: Directory to store cache database
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL,
                    created_at REAL NOT NULL
                )
                """
            )
            # Create index on expires_at for faster cleanup
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON cache(expires_at)
                """
            )
            conn.commit()

    def get(self, key: str) -> Any | None:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT value, expires_at FROM cache
                WHERE key = ?
                """,
                (key,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            value_json, expires_at = row

            # Check if expired
            if expires_at and time.time() > expires_at:
                logger.debug(f"Cache key '{key}' has expired")
                self.delete(key)
                return None

            logger.debug(f"Cache hit for key '{key}'")
            return json.loads(value_json)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (None = never expires)
        """
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl

        value_json = json.dumps(value)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, value_json, expires_at, time.time()),
            )
            conn.commit()

        logger.debug(f"Cache set for key '{key}' (TTL: {ttl}s)")

    def delete(self, key: str) -> None:
        """Delete entry from cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            logger.debug(f"Cache key '{key}' deleted")

    def clear(self) -> None:
        """Clear all cache entries"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()
            logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries deleted
        """
        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM cache
                WHERE expires_at IS NOT NULL AND expires_at < ?
                """,
                (current_time,),
            )
            deleted_count = cursor.rowcount
            conn.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired cache entries")

        return deleted_count


def create_cache(
    backend: Literal["json", "sqlite"] = "json", cache_dir: str | Path = "./data/cache"
) -> CacheBackend:
    """
    Factory function to create cache backend.

    Args:
        backend: Cache backend type ('json' or 'sqlite')
        cache_dir: Directory to store cache files

    Returns:
        Cache backend instance

    Examples:
        >>> cache = create_cache(backend="json")
        >>> cache.set("key", "value", ttl=3600)
        >>> value = cache.get("key")
    """
    if backend == "json":
        return JSONCache(cache_dir=cache_dir)
    elif backend == "sqlite":
        return SQLiteCache(cache_dir=cache_dir)
    else:
        raise ValueError(f"Unknown cache backend: {backend}. Use 'json' or 'sqlite'.")
