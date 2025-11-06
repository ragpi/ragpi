from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.connectors.common.schemas import ExtractedDocument
from src.connectors.github_pdf.schemas import PdfDocument


def chunk_pdf_document(
    *, pdf_doc: PdfDocument, chunk_size: int, chunk_overlap: int
) -> list[ExtractedDocument]:
    """
    Chunk a PDF document into smaller pieces for indexing.

    For PDFs, we use a recursive character text splitter that respects
    paragraph and sentence boundaries. Page markers are preserved to maintain context.

    Args:
        pdf_doc: The PDF document to chunk
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
            " ",  # Word breaks
            "",  # Character breaks
        ],
    )

    # Split the content into chunks
    chunks = text_splitter.split_text(pdf_doc.content)

    docs: list[ExtractedDocument] = []

    for i, chunk in enumerate(chunks, start=1):
        # Create a title that includes the file path and chunk number
        title = f"{pdf_doc.path}"
        if len(chunks) > 1:
            title += f" (Part {i}/{len(chunks)})"

        doc = ExtractedDocument(
            content=chunk,
            title=title,
            url=pdf_doc.url,
        )

        docs.append(doc)

    return docs
