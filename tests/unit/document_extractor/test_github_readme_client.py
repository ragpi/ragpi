import base64
from unittest.mock import call
import pytest
from typing import AsyncGenerator, Any
from pytest_mock import MockerFixture

from src.document_extractor.clients.github_readme import GitHubReadmeClient
from src.document_extractor.exceptions import DocumentExtractorException
from src.document_extractor.schemas import MarkdownPage


@pytest.fixture
async def github_readme_client() -> AsyncGenerator[GitHubReadmeClient, None]:
    async with GitHubReadmeClient(
        user_agent="test-agent",
        github_api_version="2022-11-28",
        github_token="test-token",
    ) as client:
        yield client


async def test_fetch_readmes_root_success(
    github_readme_client: GitHubReadmeClient,
    mocker: MockerFixture,
) -> None:
    mock_response = {
        "content": base64.b64encode(b"# Test README\nContent").decode("utf-8"),
        "encoding": "base64",
        "path": "README.md",
        "html_url": "https://github.com/test/repo/blob/main/README.md",
    }
    mock_request = mocker.patch.object(github_readme_client, "request")
    mock_request.return_value = (mock_response, {})

    readme_pages = [
        page
        async for page in github_readme_client.fetch_readmes(
            repo_owner="test",
            repo_name="repo",
        )
    ]

    assert len(readme_pages) == 1
    assert isinstance(readme_pages[0], MarkdownPage)
    assert readme_pages[0].content == "# Test README\nContent"
    assert readme_pages[0].title == "README.md"
    assert readme_pages[0].url == "https://github.com/test/repo/blob/main/README.md"

    mock_request.assert_called_once_with(
        "GET",
        "https://api.github.com/repos/test/repo/readme",
        params={},
    )


async def test_fetch_readmes_with_ref(
    github_readme_client: GitHubReadmeClient,
    mocker: MockerFixture,
) -> None:
    mock_response = {
        "content": base64.b64encode(b"# Test README\nContent").decode("utf-8"),
        "encoding": "base64",
        "path": "README.md",
        "html_url": "https://github.com/test/repo/blob/dev/README.md",
    }

    mock_request = mocker.patch.object(github_readme_client, "request")
    mock_request.return_value = (mock_response, {})

    readme_pages = [
        page
        async for page in github_readme_client.fetch_readmes(
            repo_owner="test",
            repo_name="repo",
            ref="dev",
        )
    ]

    assert len(readme_pages) == 1
    mock_request.assert_called_once_with(
        "GET",
        "https://api.github.com/repos/test/repo/readme",
        params={"ref": "dev"},
    )


async def test_fetch_readmes_subdirectories(
    github_readme_client: GitHubReadmeClient,
    mocker: MockerFixture,
) -> None:
    mock_responses: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (
            {
                "content": base64.b64encode(b"# Root README").decode("utf-8"),
                "encoding": "base64",
                "path": "README.md",
                "html_url": "https://github.com/test/repo/blob/main/README.md",
            },
            {},
        ),
        (
            {
                "content": base64.b64encode(b"# Docs README").decode("utf-8"),
                "encoding": "base64",
                "path": "docs/README.md",
                "html_url": "https://github.com/test/repo/blob/main/docs/README.md",
            },
            {},
        ),
    ]

    mock_request = mocker.patch.object(github_readme_client, "request")
    mock_request.side_effect = mock_responses

    readme_pages = [
        page
        async for page in github_readme_client.fetch_readmes(
            repo_owner="test",
            repo_name="repo",
            include_root=True,
            sub_dirs=["docs"],
        )
    ]

    assert len(readme_pages) == 2
    assert readme_pages[0].content == "# Root README"
    assert readme_pages[1].content == "# Docs README"

    assert mock_request.call_count == 2
    mock_request.assert_has_calls(
        [
            call("GET", "https://api.github.com/repos/test/repo/readme", params={}),
            call(
                "GET", "https://api.github.com/repos/test/repo/readme/docs", params={}
            ),
        ]
    )


async def test_fetch_readmes_no_directories(
    github_readme_client: GitHubReadmeClient,
) -> None:
    with pytest.raises(
        DocumentExtractorException,
        match="No directories specified to fetch READMEs",
    ):
        async for _ in github_readme_client.fetch_readmes(
            repo_owner="test",
            repo_name="repo",
            include_root=False,
        ):
            pass


async def test_fetch_readmes_request_failure(
    github_readme_client: GitHubReadmeClient,
    mocker: MockerFixture,
) -> None:
    mock_request = mocker.patch.object(github_readme_client, "request")
    mock_request.return_value = (None, None)

    with pytest.raises(
        DocumentExtractorException,
        match="Failed to fetch README content at",
    ):
        async for _ in github_readme_client.fetch_readmes(
            repo_owner="test",
            repo_name="repo",
        ):
            pass
