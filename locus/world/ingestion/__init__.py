"""U2 Ingestion — multimodal extraction into IngestionResult."""

from locus.world.ingestion.concept_art_ingestor import ConceptArtIngestor
from locus.world.ingestion.map_image_ingestor import MapImageIngestor
from locus.world.ingestion.service import IngestionService, WorldInputs, merge_results
from locus.world.ingestion.structured_map_ingestor import StructuredMapIngestor
from locus.world.ingestion.text_ingestor import TextIngestor

__all__ = [
    "ConceptArtIngestor",
    "MapImageIngestor",
    "StructuredMapIngestor",
    "TextIngestor",
    "IngestionService",
    "WorldInputs",
    "merge_results",
]
