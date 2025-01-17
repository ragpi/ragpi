from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.common.schemas import Document
from src.common.current_datetime import get_current_datetime
from src.extractors.common.stable_id import generate_stable_id
from src.extractors.github_issues.schemas import GithubIssue


def chunk_github_issue(
    *, issue: GithubIssue, chunk_size: int, chunk_overlap: int, uuid_namespace: str
) -> list[Document]:
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    issue_chunks = text_splitter.split_text(issue.body)
    docs: list[Document] = []
    created_at = get_current_datetime()

    for chunk in issue_chunks:
        doc = Document(
            id=generate_stable_id(uuid_namespace, issue.url, chunk),
            content=chunk,
            title=issue.title,
            url=issue.url,
            created_at=created_at,
        )
        docs.append(doc)

    for comment in issue.comments:
        comment_chunks = text_splitter.split_text(comment.body)

        for chunk in comment_chunks:
            doc = Document(
                id=generate_stable_id(uuid_namespace, comment.url, chunk),
                content=chunk,
                title=issue.title,
                url=comment.url,
                created_at=created_at,
            )
            docs.append(doc)

    return docs
