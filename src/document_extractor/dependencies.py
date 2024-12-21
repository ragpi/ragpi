from src.config import Settings
from src.document_extractor.service import DocumentExtractor


def get_document_extractor(settings: Settings) -> DocumentExtractor:
    return DocumentExtractor(settings)
