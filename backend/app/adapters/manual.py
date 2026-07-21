"""
Manual import adapter — handles pasted links and researcher-entered data.
"""
from typing import Dict, Any, List, Optional
from app.adapters.base import VideoAdapter, AdapterResult
from app.utils.url_parser import parse_video_url
from app.utils.validators import (
    safe_int, safe_bool, validate_publish_time, validate_platform
)


class ManualImportAdapter(VideoAdapter):
    """Adapter for manual link paste and form-based data entry."""

    name = "manual_import"
    collection_method = "manual_import"

    async def extract(self, input_data: Any) -> AdapterResult:
        """
        Extract from a URL string or a dict with url + metadata.
        """
        result = AdapterResult(success=False)

        url = None
        metadata = {}

        if isinstance(input_data, str):
            url = input_data
        elif isinstance(input_data, dict):
            url = input_data.get("video_url") or input_data.get("url")
            metadata = input_data
        else:
            result.errors.append(f"Expected str or dict, got {type(input_data)}")
            return result

        if not url:
            result.errors.append("No video URL provided")
            return result

        # Parse URL to get platform and video ID
        parsed = parse_video_url(url)
        if not parsed:
            result.errors.append(f"Cannot parse URL as Douyin or Kuaishou link: {url}")
            return result

        video_data = {
            "platform": parsed.platform,
            "platform_video_id": parsed.platform_video_id,
            "video_url": url if not parsed.is_short_url else metadata.get("video_url"),
            "short_url": url if parsed.is_short_url else metadata.get("short_url"),
        }

        # Merge metadata fields (these are researcher-provided)
        mergeable_fields = [
            "video_title", "video_description", "hashtags",
            "publish_time", "duration_seconds", "cover_url",
            "collection_keyword", "search_result_rank",
            "search_sort_mode", "search_date",
        ]
        for field in mergeable_fields:
            if field in metadata and metadata[field] is not None:
                if field == "publish_time":
                    parsed_time = validate_publish_time(metadata[field])
                    if parsed_time:
                        video_data[field] = parsed_time
                elif field == "hashtags":
                    if isinstance(metadata[field], str):
                        video_data[field] = [t.strip() for t in metadata[field].split(",") if t.strip()]
                    elif isinstance(metadata[field], list):
                        video_data[field] = metadata[field]
                elif field in ("duration_seconds", "search_result_rank"):
                    video_data[field] = safe_int(metadata[field])
                else:
                    video_data[field] = metadata[field]

        result.video_data = video_data
        result.success = True
        return result

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            **super().get_capabilities(),
            "supports_comments": True,  # User can paste comments manually
            "supports_metrics": True,  # User can type visible metrics
            "supports_author_details": True,  # User can enter author info
            "requires_auth": False,
            "compliance_notes": "All data must be publicly visible to the researcher",
        }
