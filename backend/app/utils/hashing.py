"""
SHA-256 hashing utility for de-identification.
All platform-native user IDs and comment IDs are hashed before storage.
"""
import hashlib


def hash_id(raw_id: str, salt: str = "") -> str:
    """
    Hash a raw platform ID using SHA-256.
    Optionally salted with a project-level secret.

    Args:
        raw_id: The raw platform ID string.
        salt: Optional salt (project-level, not per-record).

    Returns:
        64-character hex SHA-256 hash.
    """
    if not raw_id:
        return ""
    combined = f"{salt}:{raw_id}" if salt else raw_id
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def hash_author_id(platform_author_id: str) -> str:
    """Hash a platform author ID for storage."""
    return hash_id(platform_author_id)


def hash_commenter_id(platform_commenter_id: str) -> str:
    """Hash a platform commenter ID for storage."""
    return hash_id(platform_commenter_id)


def hash_comment_id(platform_comment_id: str) -> str:
    """Hash a platform comment ID for storage."""
    return hash_id(platform_comment_id)
