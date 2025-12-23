"""Unit tests for cache utilities"""

import json
import sqlite3
import time

import pytest

from b3quant.utils.cache import JSONCache, SQLiteCache, create_cache


class TestJSONCache:
    """Tests for JSON-based cache"""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory"""
        return tmp_path / "cache"

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create JSON cache instance"""
        return JSONCache(cache_dir=temp_cache_dir)

    def test_set_and_get(self, cache):
        """Test basic set and get operations"""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self, cache):
        """Test get returns None for nonexistent key"""
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self, cache):
        """Test that entries expire after TTL"""
        cache.set("key", "value", ttl=1)  # 1 second TTL
        assert cache.get("key") == "value"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key") is None

    def test_ttl_not_expired(self, cache):
        """Test that entries don't expire before TTL"""
        cache.set("key", "value", ttl=10)
        time.sleep(0.1)
        assert cache.get("key") == "value"

    def test_no_ttl(self, cache):
        """Test entries without TTL don't expire"""
        cache.set("key", "value", ttl=None)
        time.sleep(0.5)
        assert cache.get("key") == "value"

    def test_complex_value(self, cache):
        """Test caching complex data structures"""
        value = {"nested": {"data": [1, 2, 3]}, "list": ["a", "b", "c"]}
        cache.set("complex", value)
        assert cache.get("complex") == value

    def test_delete(self, cache):
        """Test deleting entries"""
        cache.set("key", "value")
        assert cache.get("key") == "value"

        cache.delete("key")
        assert cache.get("key") is None

    def test_clear(self, cache):
        """Test clearing all entries"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cleanup_expired(self, cache):
        """Test cleanup removes only expired entries"""
        cache.set("expired1", "value1", ttl=1)
        cache.set("expired2", "value2", ttl=1)
        cache.set("valid", "value3", ttl=10)

        time.sleep(1.1)

        count = cache.cleanup_expired()
        assert count == 2
        assert cache.get("valid") == "value3"

    def test_persistence(self, temp_cache_dir):
        """Test that cache persists across instances"""
        cache1 = JSONCache(cache_dir=temp_cache_dir)
        cache1.set("persistent", "value")

        # Create new instance
        cache2 = JSONCache(cache_dir=temp_cache_dir)
        assert cache2.get("persistent") == "value"

    def test_cache_file_created(self, temp_cache_dir):
        """Test that cache file is created"""
        cache = JSONCache(cache_dir=temp_cache_dir)
        cache.set("key", "value")

        cache_file = temp_cache_dir / "cache.json"
        assert cache_file.exists()

        # Verify file content
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
            assert "key" in data


class TestSQLiteCache:
    """Tests for SQLite-based cache"""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory"""
        return tmp_path / "cache"

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create SQLite cache instance"""
        return SQLiteCache(cache_dir=temp_cache_dir)

    def test_set_and_get(self, cache):
        """Test basic set and get operations"""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self, cache):
        """Test get returns None for nonexistent key"""
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self, cache):
        """Test that entries expire after TTL"""
        cache.set("key", "value", ttl=1)
        assert cache.get("key") == "value"

        time.sleep(1.1)
        assert cache.get("key") is None

    def test_ttl_not_expired(self, cache):
        """Test that entries don't expire before TTL"""
        cache.set("key", "value", ttl=10)
        time.sleep(0.1)
        assert cache.get("key") == "value"

    def test_no_ttl(self, cache):
        """Test entries without TTL don't expire"""
        cache.set("key", "value", ttl=None)
        time.sleep(0.5)
        assert cache.get("key") == "value"

    def test_complex_value(self, cache):
        """Test caching complex data structures"""
        value = {"nested": {"data": [1, 2, 3]}, "list": ["a", "b", "c"]}
        cache.set("complex", value)
        assert cache.get("complex") == value

    def test_delete(self, cache):
        """Test deleting entries"""
        cache.set("key", "value")
        assert cache.get("key") == "value"

        cache.delete("key")
        assert cache.get("key") is None

    def test_clear(self, cache):
        """Test clearing all entries"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cleanup_expired(self, cache):
        """Test cleanup removes only expired entries"""
        cache.set("expired1", "value1", ttl=1)
        cache.set("expired2", "value2", ttl=1)
        cache.set("valid", "value3", ttl=10)

        time.sleep(1.1)

        count = cache.cleanup_expired()
        assert count == 2
        assert cache.get("valid") == "value3"

    def test_persistence(self, temp_cache_dir):
        """Test that cache persists across instances"""
        cache1 = SQLiteCache(cache_dir=temp_cache_dir)
        cache1.set("persistent", "value")

        # Create new instance
        cache2 = SQLiteCache(cache_dir=temp_cache_dir)
        assert cache2.get("persistent") == "value"

    def test_db_file_created(self, temp_cache_dir):
        """Test that database file is created"""
        cache = SQLiteCache(cache_dir=temp_cache_dir)
        cache.set("key", "value")

        db_file = temp_cache_dir / "cache.db"
        assert db_file.exists()

    def test_upsert_behavior(self, cache):
        """Test that set replaces existing values"""
        cache.set("key", "value1")
        assert cache.get("key") == "value1"

        cache.set("key", "value2")
        assert cache.get("key") == "value2"

    def test_schema_exists(self, temp_cache_dir):
        """Test that database schema is created correctly"""
        cache = SQLiteCache(cache_dir=temp_cache_dir)

        with sqlite3.connect(cache.db_path) as conn:
            # Check table exists
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='cache'
                """
            )
            assert cursor.fetchone() is not None

            # Check index exists
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='index' AND name='idx_expires_at'
                """
            )
            assert cursor.fetchone() is not None


class TestCacheFactory:
    """Tests for cache factory function"""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory"""
        return tmp_path / "cache"

    def test_create_json_cache(self, temp_cache_dir):
        """Test creating JSON cache via factory"""
        cache = create_cache(backend="json", cache_dir=temp_cache_dir)
        assert isinstance(cache, JSONCache)

    def test_create_sqlite_cache(self, temp_cache_dir):
        """Test creating SQLite cache via factory"""
        cache = create_cache(backend="sqlite", cache_dir=temp_cache_dir)
        assert isinstance(cache, SQLiteCache)

    def test_invalid_backend_raises_error(self, temp_cache_dir):
        """Test that invalid backend raises ValueError"""
        with pytest.raises(ValueError, match="Unknown cache backend"):
            create_cache(backend="invalid", cache_dir=temp_cache_dir)

    def test_default_backend(self, temp_cache_dir):
        """Test default backend is JSON"""
        cache = create_cache(cache_dir=temp_cache_dir)
        assert isinstance(cache, JSONCache)


class TestCacheBackendParity:
    """Test that both backends behave identically"""

    @pytest.fixture(params=["json", "sqlite"])
    def cache(self, request, tmp_path):
        """Parametrized fixture for both cache backends"""
        cache_dir = tmp_path / f"cache_{request.param}"
        return create_cache(backend=request.param, cache_dir=cache_dir)

    def test_basic_operations(self, cache):
        """Test that basic operations work the same across backends"""
        cache.set("key", "value")
        assert cache.get("key") == "value"

        cache.delete("key")
        assert cache.get("key") is None

    def test_ttl_behavior(self, cache):
        """Test that TTL works the same across backends"""
        cache.set("temp", "value", ttl=1)
        assert cache.get("temp") == "value"

        time.sleep(1.1)
        assert cache.get("temp") is None

    def test_cleanup(self, cache):
        """Test that cleanup works the same across backends"""
        cache.set("expired", "value", ttl=1)
        cache.set("valid", "value", ttl=10)

        time.sleep(1.1)

        count = cache.cleanup_expired()
        assert count == 1
        assert cache.get("valid") == "value"
