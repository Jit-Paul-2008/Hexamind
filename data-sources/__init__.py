"""Data source ingestion and extraction."""

from .ingestors import UniversalIngestor
from .extraction import DataExtractor
from .inventory import SourceInventory
from .cache import DeduplicationCache

__all__ = ["UniversalIngestor", "DataExtractor", "SourceInventory", "DeduplicationCache"]
