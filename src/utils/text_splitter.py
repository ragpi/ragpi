import uuid
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.schemas.collections import CollectionDocument
from src.schemas.page_data import PageData


def split_markdown_content(page_data: PageData) -> list[CollectionDocument]:
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
        chunk_size=1000, chunk_overlap=200, add_start_index=True
    )

    splits = text_splitter.split_documents(md_header_splits)

    docs: list[CollectionDocument] = []

    # TODO: Update typings for split.metadata
    for split in splits:
        docs.append(
            CollectionDocument(
                id=uuid.uuid4(),
                content=split.page_content,
                source=page_data.url,
                title=page_data.title,
                header_1=(
                    split.metadata["header_1"] if "header_1" in split.metadata else None  # type: ignore
                ),
                header_2=(
                    split.metadata["header_2"] if "header_2" in split.metadata else None  # type: ignore
                ),
                header_3=(
                    split.metadata["header_3"] if "header_3" in split.metadata else None  # type: ignore
                ),
            )
        )

    return docs
