"""
Tests for hashing utility.
"""
import pytest
from app.utils.hashing import hash_id, hash_author_id, hash_commenter_id, hash_comment_id


class TestHashing:
    def test_hash_id_deterministic(self):
        """Same input should always produce same hash."""
        h1 = hash_id("user_12345")
        h2 = hash_id("user_12345")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 produces 64 hex chars

    def test_hash_id_different_inputs(self):
        """Different inputs should produce different hashes."""
        h1 = hash_id("user_12345")
        h2 = hash_id("user_67890")
        assert h1 != h2

    def test_hash_id_with_salt(self):
        """Salted hash should differ from unsalted."""
        h1 = hash_id("user_12345")
        h2 = hash_id("user_12345", salt="project_salt")
        assert h1 != h2

    def test_hash_id_empty_string(self):
        """Empty string should return empty string."""
        assert hash_id("") == ""

    def test_hash_author_id(self):
        h = hash_author_id("platform_author_001")
        assert len(h) == 64

    def test_hash_commenter_id(self):
        h = hash_commenter_id("platform_commenter_001")
        assert len(h) == 64

    def test_hash_comment_id(self):
        h = hash_comment_id("platform_comment_001")
        assert len(h) == 64


class TestPrivacy:
    def test_raw_id_not_visible_in_hash(self):
        """Hash should be one-way — can't reconstruct original ID."""
        raw = "super_secret_user_id"
        h = hash_id(raw)
        assert raw not in h
        # SHA-256 length
        assert len(h) == 64

    def test_different_salts_isolate_datasets(self):
        """Different research projects using different salts get different hashes."""
        raw = "user_001"
        project_a = hash_id(raw, salt="project_a")
        project_b = hash_id(raw, salt="project_b")
        assert project_a != project_b
