from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.connectors.common.schemas import ExtractedDocument
from src.connectors.github_issues.schemas import GithubIssue


def chunk_github_issue(
    *, issue: GithubIssue, chunk_size: int, chunk_overlap: int
) -> list[ExtractedDocument]:
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    issue_chunks = text_splitter.split_text(issue.body)
    docs: list[ExtractedDocument] = []

    for chunk in issue_chunks:
        doc = ExtractedDocument(
            content=chunk,
            title=issue.title,
            url=issue.url,
        )
        docs.append(doc)

    for comment in issue.comments:
        comment_chunks = text_splitter.split_text(comment.body)

        for chunk in comment_chunks:
            doc = ExtractedDocument(
                content=chunk,
                title=issue.title,
                url=comment.url,
            )
            docs.append(doc)

    return docs
