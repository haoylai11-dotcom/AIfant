"""
Tests for validators utility.
"""
import pytest
from datetime import datetime
from app.utils.validators import (
    validate_platform, validate_unavailable_reason,
    validate_collection_method, validate_verification_status,
    validate_metric_visibility, safe_int, safe_bool,
    validate_publish_time,
)


class TestValidatePlatform:
    def test_valid_platforms(self):
        assert validate_platform("douyin") is True
        assert validate_platform("kuaishou") is True

    def test_invalid_platforms(self):
        assert validate_platform("youtube") is False
        assert validate_platform("tiktok") is False
        assert validate_platform("") is False


class TestValidateUnavailableReason:
    def test_valid_reasons(self):
        assert validate_unavailable_reason("deleted_by_author") is True
        assert validate_unavailable_reason("removed_by_platform") is True
        assert validate_unavailable_reason("unknown") is True

    def test_null_is_valid(self):
        assert validate_unavailable_reason(None) is True

    def test_invalid_reason(self):
        assert validate_unavailable_reason("not_a_reason") is False


class TestValidateMetricVisibility:
    def test_valid_visibility(self):
        visibility = {
            "like_count": "visible",
            "comment_count": "visible",
            "share_count": "unavailable_not_displayed",
            "favorite_count": "unavailable_platform_restricted",
            "view_count": "visible",
        }
        assert validate_metric_visibility(visibility) is True

    def test_invalid_key(self):
        assert validate_metric_visibility({"wrong_key": "visible"}) is False

    def test_invalid_value(self):
        assert validate_metric_visibility({"like_count": "not_a_value"}) is False

    def test_empty_dict(self):
        assert validate_metric_visibility({}) is True


class TestSafeInt:
    def test_valid_int(self):
        assert safe_int("123") == 123
        assert safe_int(456) == 456

    def test_null_cases(self):
        assert safe_int(None) is None
        assert safe_int("") is None

    def test_invalid_string(self):
        assert safe_int("abc") is None
        assert safe_int("12.5") is None


class TestSafeBool:
    def test_true_values(self):
        assert safe_bool("true") is True
        assert safe_bool("1") is True
        assert safe_bool("yes") is True
        assert safe_bool("是") is True
        assert safe_bool(True) is True

    def test_false_values(self):
        assert safe_bool("false") is False
        assert safe_bool("0") is False
        assert safe_bool("no") is False
        assert safe_bool("否") is False
        assert safe_bool(False) is False

    def test_null_values(self):
        assert safe_bool(None) is None
        assert safe_bool("") is None


class TestValidatePublishTime:
    def test_iso_format(self):
        dt = validate_publish_time("2024-01-15T10:30:00")
        assert dt == datetime(2024, 1, 15, 10, 30, 0)

    def test_date_only(self):
        dt = validate_publish_time("2024-01-15")
        assert dt == datetime(2024, 1, 15)

    def test_slash_format(self):
        dt = validate_publish_time("2024/01/15 10:30:00")
        assert dt == datetime(2024, 1, 15, 10, 30, 0)

    def test_invalid_format(self):
        dt = validate_publish_time("not a date")
        assert dt is None

    def test_null(self):
        dt = validate_publish_time(None)
        assert dt is None
