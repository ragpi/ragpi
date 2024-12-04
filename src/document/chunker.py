from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.document.id_generator import generate_stable_id
from src.document.schemas import Document, GithubIssue, MarkdownPage


def chunk_github_issue(
    issue: GithubIssue, chunk_size: int, chunk_overlap: int
) -> list[Document]:
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    issue_chunks = text_splitter.split_text(issue.body)

    docs: list[Document] = []

    for chunk in issue_chunks:
        doc = Document(
            id=generate_stable_id(issue.url, chunk),
            content=chunk,
            metadata={
                "url": issue.url,
                "title": issue.title,
            },
        )

        docs.append(doc)

    for comment in issue.comments:
        comment_chunks = text_splitter.split_text(comment.body)

        for chunk in comment_chunks:
            doc = Document(
                id=generate_stable_id(comment.url, chunk),
                content=chunk,
                metadata={
                    "url": comment.url,
                    "title": issue.title,
                },
            )

            docs.append(doc)

    return docs


def chunk_markdown_page(
    page_data: MarkdownPage, chunk_size: int, chunk_overlap: int
) -> list[Document]:
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

    docs: list[Document] = []

    for chunk in chunks:
        metadata = chunk.metadata  # type: ignore
        title = page_data.title

        if "header_1" in metadata:
            title += f" - {metadata['header_1']}"
        if "header_2" in metadata:
            title += f" - {metadata['header_2']}"
        if "header_3" in metadata:
            title += f" - {metadata['header_3']}"

        doc = Document(
            id=generate_stable_id(page_data.url, chunk.page_content),
            content=chunk.page_content,
            metadata={
                "url": page_data.url,
                "title": title,
            },
        )

        docs.append(doc)

    return docs
