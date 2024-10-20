from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.schemas.repository import RepositoryDocument
from src.schemas.page_data import PageData
from src.utils.generate_id import generate_stable_id


def split_markdown_content(
    page_data: PageData, chunk_size: int, chunk_overlap: int
) -> list[RepositoryDocument]:
    headers_to_split_on = [
        ("#", "header_1"),
        ("##", "header_2"),
        ("###", "header_3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on, strip_headers=False
    )

    md_header_splits = markdown_splitter.split_text(page_data.content)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    splits = text_splitter.split_documents(md_header_splits)

    docs: list[RepositoryDocument] = []

    for split in splits:
        doc = RepositoryDocument(
            id=generate_stable_id(page_data.url, split.page_content),
            content=split.page_content,
            metadata={
                "url": page_data.url,
                "title": page_data.title,
            },
        )

        if "header_1" in split.metadata:  # type: ignore
            doc.metadata["header_1"] = split.metadata["header_1"]  # type: ignore
        if "header_2" in split.metadata:  # type: ignore
            doc.metadata["header_2"] = split.metadata["header_2"]  # type: ignore
        if "header_3" in split.metadata:  # type: ignore
            doc.metadata["header_3"] = split.metadata["header_3"]  # type: ignore

        docs.append(doc)

    return docs
