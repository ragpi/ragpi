from chonkie import SentenceChunker  # type: ignore

from src.document.id_generator import generate_stable_id
from src.document.schemas import Document, GithubIssue, MarkdownPage


def chunk_github_issue_data(
    issue: GithubIssue, chunk_size: int, chunk_overlap: int
) -> list[Document]:
    chunker = SentenceChunker(
        tokenizer="gpt2",
        min_chunk_size=2,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    issue_chunks = chunker.chunk(issue.body)

    docs: list[Document] = []

    for chunk in issue_chunks:
        doc = Document(
            id=generate_stable_id(issue.url, chunk.text),
            content=chunk.text,
            metadata={
                "url": issue.url,
                "title": issue.title,
            },
        )

        docs.append(doc)

    for comment in issue.comments:
        comment_chunks = chunker.chunk(comment.body)

        for chunk in comment_chunks:
            doc = Document(
                id=generate_stable_id(comment.url, chunk.text),
                content=chunk.text,
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
    chunker = SentenceChunker(
        tokenizer="gpt2",
        min_chunk_size=2,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    page_chunks = chunker.chunk(page_data.content)

    docs: list[Document] = []

    for chunk in page_chunks:
        doc = Document(
            id=generate_stable_id(page_data.url, chunk.text),
            content=chunk.text,
            metadata={
                "url": page_data.url,
                "title": page_data.title,
            },
        )

        docs.append(doc)

    return docs
