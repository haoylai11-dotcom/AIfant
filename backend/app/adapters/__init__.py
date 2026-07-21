"""
Adapters package.
"""
from app.adapters.base import VideoAdapter, AdapterResult
from app.adapters.manual import ManualImportAdapter
from app.adapters.browser_extract import BrowserExtractAdapter

__all__ = [
    "VideoAdapter",
    "AdapterResult",
    "ManualImportAdapter",
    "BrowserExtractAdapter",
]
