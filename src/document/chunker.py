from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.document.id_generator import generate_stable_id
from src.document.schemas import Document, PageData


def split_markdown_page(
    page_data: PageData, chunk_size: int, chunk_overlap: int
) -> list[Document]:
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

    docs: list[Document] = []

    for split in splits:
        metadata = split.metadata  # type: ignore
        title = page_data.title

        if "header_1" in metadata:
            title += f" - {metadata['header_1']}"
        if "header_2" in metadata:
            title += f" - {metadata['header_2']}"
        if "header_3" in metadata:
            title += f" - {metadata['header_3']}"

        doc = Document(
            id=generate_stable_id(page_data.url, split.page_content),
            content=split.page_content,
            metadata={
                "url": page_data.url,
                "title": title,
            },
        )

        docs.append(doc)

    return docs
