from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List

from src.connectors.common.schemas import ExtractedDocument

def chunk_pdf_page(*, page_text: str, url: str, page_title: str, chunk_size: int, chunk_overlap: int) -> List[ExtractedDocument]:
    """Chunks PDF page text into smaller documents."""
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    chunks = text_splitter.split_text(page_text)
    docs: List[ExtractedDocument] = []

    for i, chunk in enumerate(chunks):
        doc = ExtractedDocument(
            content=chunk,
            title=f"{page_title} - Chunk {i+1}", 
            url=url,
        )
        docs.append(doc)
    return docs

