"""
Adapter abstract base class.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class AdapterResult:
    """Result from any adapter's extract/import operation."""
    success: bool
    video_data: Optional[Dict[str, Any]] = None
    author_data: Optional[Dict[str, Any]] = None
    metric_data: Optional[Dict[str, Any]] = None
    comments_data: Optional[List[Dict[str, Any]]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class VideoAdapter(ABC):
    """Abstract base for all data collection adapters."""

    name: str = "base_adapter"
    collection_method: str = "unknown"

    @abstractmethod
    async def extract(self, input_data: Any) -> AdapterResult:
        """
        Extract video data from the given input.
        For browser_extract: input is JSON from page extraction.
        For manual: input is a URL string.
        For csv: input is a parsed row dict.
        """
        ...

    def get_capabilities(self) -> Dict[str, Any]:
        """Return what this adapter can and cannot provide."""
        return {
            "adapter_name": self.name,
            "collection_method": self.collection_method,
            "supports_comments": False,
            "supports_metrics": False,
            "supports_author_details": False,
            "requires_auth": False,
            "compliance_notes": "",
        }
