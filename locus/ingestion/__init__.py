"""U2 Ingestion — multimodal extraction into IngestionResult."""

from .concept_art_ingestor import ConceptArtIngestor
from .map_image_ingestor import MapImageIngestor
from .service import IngestionService, WorldInputs, merge_results
from .structured_map_ingestor import StructuredMapIngestor
from .text_ingestor import TextIngestor

__all__ = [
    "ConceptArtIngestor",
    "MapImageIngestor",
    "StructuredMapIngestor",
    "TextIngestor",
    "IngestionService",
    "WorldInputs",
    "merge_results",
]
