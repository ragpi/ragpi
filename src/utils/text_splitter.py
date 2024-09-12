from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.schemas.page_data import PageData


def split_markdown_content(page_data: PageData) -> list[Document]:
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on, strip_headers=False
    )

    md_header_splits = markdown_splitter.split_text(page_data.content)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, add_start_index=True
    )

    splits = text_splitter.split_documents(md_header_splits)

    # TODO: Create custom Document class that can handle metadata?
    for split in splits:
        split.metadata["source"] = page_data.url  # type: ignore
        split.metadata["title"] = page_data.title  # type: ignore

    return splits
