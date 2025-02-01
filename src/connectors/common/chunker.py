from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.connectors.common.schemas import ExtractedDocument, MarkdownPage


def chunk_markdown_page(
    *, page_data: MarkdownPage, chunk_size: int, chunk_overlap: int
) -> list[ExtractedDocument]:
    headers_to_split_on = [
        ("#", "header_1"),
        ("##", "header_2"),
        ("###", "header_3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on, strip_headers=False
    )

    header_chunks = markdown_splitter.split_text(page_data.content)

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    chunks = text_splitter.split_documents(header_chunks)

    docs: list[ExtractedDocument] = []

    for chunk in chunks:
        metadata = chunk.metadata  # type: ignore
        title = page_data.title

        if "header_1" in metadata:
            title += f" - {metadata['header_1']}"
        if "header_2" in metadata:
            title += f" - {metadata['header_2']}"
        if "header_3" in metadata:
            title += f" - {metadata['header_3']}"

        doc = ExtractedDocument(
            content=chunk.page_content,
            title=title,
            url=page_data.url,
        )

        docs.append(doc)

    return docs
