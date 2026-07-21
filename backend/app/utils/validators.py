"""
Validators for video data fields.
"""
from typing import Optional, Any
from datetime import datetime


# Valid unavailable_reason values
UNAVAILABLE_REASONS = {
    "deleted_by_author",
    "removed_by_platform",
    "private_or_permission_changed",
    "link_invalid",
    "region_or_login_restricted",
    "unknown",
}

# Valid collection_method values
COLLECTION_METHODS = {
    "official_api",
    "researcher_browser",
    "manual_import",
    "licensed_provider",
}

# Valid verification_status values
VERIFICATION_STATUSES = {
    "unverified",
    "verified",
    "needs_review",
    "flagged",
}

# Valid coding_status values
CODING_STATUSES = {
    "uncoded",
    "in_progress",
    "coded",
    "needs_review",
}

# Valid user roles
USER_ROLES = {"admin", "coder", "viewer"}

# Valid sort modes
SORT_MODES = {"comprehensive", "hot", "latest", "manual"}


def validate_platform(platform: str) -> bool:
    """Platform must be 'douyin' or 'kuaishou'."""
    return platform in {"douyin", "kuaishou"}


def validate_unavailable_reason(reason: Optional[str]) -> bool:
    """Check if unavailable_reason is a valid value."""
    if reason is None:
        return True
    return reason in UNAVAILABLE_REASONS


def validate_collection_method(method: str) -> bool:
    return method in COLLECTION_METHODS


def validate_verification_status(status: str) -> bool:
    return status in VERIFICATION_STATUSES


def validate_metric_visibility(visibility: dict) -> bool:
    """Validate metric_visibility JSON structure."""
    allowed_values = {
        "visible",
        "unavailable_not_displayed",
        "unavailable_not_authorized",
        "unavailable_platform_restricted",
        "unavailable_parse_failed",
    }
    if not isinstance(visibility, dict):
        return False
    valid_keys = {"like_count", "comment_count", "share_count",
                  "favorite_count", "view_count"}
    for key, value in visibility.items():
        if key not in valid_keys:
            return False
        if value not in allowed_values:
            return False
    return True


def validate_publish_time(time_str: Optional[str]) -> Optional[datetime]:
    """Try to parse a publish time string. Returns None on failure."""
    if time_str is None:
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(time_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def safe_int(value: Any) -> Optional[int]:
    """Convert to int, return None on failure."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_bool(value: Any) -> Optional[bool]:
    """Convert to bool, return None on failure."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1", "yes", "是"):
            return True
        if v in ("false", "0", "no", "否"):
            return False
    try:
        return bool(int(value))
    except (ValueError, TypeError):
        return None
