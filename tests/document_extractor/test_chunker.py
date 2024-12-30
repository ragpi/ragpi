import pytest
from datetime import datetime
from pytest_mock import MockerFixture

from src.document_extractor.schemas import MarkdownPage, GithubIssue, GithubIssueComment
from src.document_extractor.chunker import Chunker


@pytest.fixture
def chunker() -> Chunker:
    return Chunker(
        chunk_size=1000,
        chunk_overlap=100,
        uuid_namespace="ee747eb2-fd0f-4650-9785-a2e9ae036ff2",
    )


@pytest.fixture
def mock_current_datetime() -> str:
    return datetime(2024, 1, 1, 12, 0, 0).isoformat()


@pytest.fixture
def mock_stable_id() -> str:
    return "stable-id"


@pytest.fixture
def sample_markdown_page() -> MarkdownPage:
    return MarkdownPage(
        url="https://example.com/doc",
        title="Test Document",
        content="""# Header 1
This is content under header 1
## Header 2
This is content under header 2
### Header 3
This is content under header 3""",
    )


@pytest.fixture
def sample_github_issue() -> GithubIssue:
    return GithubIssue(
        id="1",
        url="https://github.com/org/repo/issues/1",
        title="Test Issue",
        body="This is the main issue body with some content.",
        comments=[
            GithubIssueComment(
                id="1",
                url="https://github.com/org/repo/issues/1#comment-1",
                body="This is a comment on the issue.",
            ),
            GithubIssueComment(
                id="2",
                url="https://github.com/org/repo/issues/1#comment-2",
                body="This is another comment.",
            ),
        ],
    )


async def test_chunk_markdown_page(
    chunker: Chunker,
    sample_markdown_page: MarkdownPage,
    mock_current_datetime: datetime,
    mock_stable_id: str,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "src.document_extractor.chunker.get_current_datetime",
        return_value=mock_current_datetime,
    )
    mocker.patch(
        "src.document_extractor.chunker.generate_stable_id",
        return_value=mock_stable_id,
    )

    result = chunker.chunk_markdown_page(sample_markdown_page)

    # Chunk 1
    assert result[0].id == mock_stable_id
    assert result[0].title == "Test Document - Header 1"
    assert result[0].content == "# Header 1\nThis is content under header 1"
    assert result[0].url == "https://example.com/doc"
    assert result[0].created_at == mock_current_datetime

    # Chunk 2
    assert result[1].id == mock_stable_id
    assert result[1].title == "Test Document - Header 1 - Header 2"
    assert result[1].content == "## Header 2\nThis is content under header 2"
    assert result[1].url == "https://example.com/doc"
    assert result[1].created_at == mock_current_datetime

    # Chunk 3
    assert result[2].id == mock_stable_id
    assert result[2].title == "Test Document - Header 1 - Header 2 - Header 3"
    assert result[2].content == "### Header 3\nThis is content under header 3"
    assert result[2].url == "https://example.com/doc"
    assert result[2].created_at == mock_current_datetime


async def test_chunk_github_issue(
    chunker: Chunker,
    sample_github_issue: GithubIssue,
    mock_current_datetime: datetime,
    mock_stable_id: str,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "src.document_extractor.chunker.get_current_datetime",
        return_value=mock_current_datetime,
    )
    mocker.patch(
        "src.document_extractor.chunker.generate_stable_id",
        return_value=mock_stable_id,
    )

    result = chunker.chunk_github_issue(sample_github_issue)

    # Main issue body
    assert result[0].id == mock_stable_id
    assert result[0].title == sample_github_issue.title
    assert result[0].content == sample_github_issue.body
    assert result[0].url == sample_github_issue.url
    assert result[0].created_at == mock_current_datetime

    # Comment 1
    assert result[1].id == mock_stable_id
    assert result[1].title == sample_github_issue.title
    assert result[1].content == sample_github_issue.comments[0].body
    assert result[1].url == sample_github_issue.comments[0].url
    assert result[1].created_at == mock_current_datetime

    # Comment 2
    assert result[2].id == mock_stable_id
    assert result[2].title == sample_github_issue.title
    assert result[2].content == sample_github_issue.comments[1].body
    assert result[2].url == sample_github_issue.comments[1].url
    assert result[2].created_at == mock_current_datetime
