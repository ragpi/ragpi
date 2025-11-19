from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.connectors.common.schemas import ExtractedDocument
from src.connectors.restful.schemas import RestfulDocument


def chunk_restful_document(
    *, restful_doc: RestfulDocument, chunk_size: int, chunk_overlap: int
) -> list[ExtractedDocument]:
    """
    Chunk a RESTful API document into smaller pieces for indexing.

    For JSON content from APIs, we use a recursive character text splitter
    that respects natural boundaries like paragraphs, lines, and sentences.
    If the content is already small enough, it won't be split.

    Args:
        restful_doc: The RESTful document to chunk
        chunk_size: Maximum size of each chunk in tokens
        chunk_overlap: Number of overlapping tokens between chunks

    Returns:
        List of extracted document chunks
    """
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",  # Paragraph breaks
            "\n",  # Line breaks
            ". ",  # Sentence breaks
            ", ",  # Clause breaks
            " ",  # Word breaks
            "",  # Character breaks
        ],
    )

    # Split the content into chunks
    chunks = text_splitter.split_text(restful_doc.content)

    docs: list[ExtractedDocument] = []

    for i, chunk in enumerate(chunks, start=1):
        # Create a title that includes the original title and chunk number
        title = restful_doc.title
        if len(chunks) > 1:
            title += f" (Part {i}/{len(chunks)})"

        doc = ExtractedDocument(
            content=chunk,
            title=title,
            url=restful_doc.url,
        )

        docs.append(doc)

    return docs
