from unittest.mock import call
import pytest
from datetime import datetime, timedelta
from typing import Any
from pytest_mock import MockerFixture

from src.connectors.common.github_client import GitHubClient
from src.connectors.github_issues.fetcher import GitHubIssuesFetcher
from src.connectors.github_issues.schemas import GithubIssue


@pytest.fixture
async def github_issue_fetcher(
    github_client: GitHubClient,
) -> GitHubIssuesFetcher:
    return GitHubIssuesFetcher(github_client=github_client)


async def test_fetch_comments(
    github_issue_fetcher: GitHubIssuesFetcher,
    mocker: MockerFixture,
) -> None:
    mock_responses: list[tuple[list[dict[str, Any]], dict[str, str]]] = [
        # First page with 1 comment and a link to the next page
        (
            [{"id": 1, "html_url": "url1", "body": "First comment"}],
            {
                "Link": '<https://api.github.com/repos/test/repo/issues/1/comments?page=2&per_page=100>; rel="next"'
            },
        ),
        # Second page with 1 comment and no link to the next page
        (
            [{"id": 2, "html_url": "url2", "body": "Second comment"}],
            {},
        ),
    ]

    mock_request = mocker.patch.object(github_issue_fetcher.client, "request")
    mock_request.side_effect = mock_responses

    comments = await github_issue_fetcher.fetch_comments(
        "https://api.github.com/repos/test/repo/issues/1/comments"
    )

    assert len(comments) == 2
    assert comments[0].id == "1"
    assert comments[0].body == "First comment"
    assert comments[1].id == "2"
    assert comments[1].body == "Second comment"
    mock_request.assert_has_calls(
        [
            call(
                "GET",
                "https://api.github.com/repos/test/repo/issues/1/comments",
                params={"per_page": "100"},
            ),
            # All subsequent requests don't need params as they are included in the URL from the Link header
            call(
                "GET",
                "https://api.github.com/repos/test/repo/issues/1/comments?page=2&per_page=100",
                params=None,
            ),
        ]
    )


async def test_fetch_issues_basic(
    github_issue_fetcher: GitHubIssuesFetcher,
    mocker: MockerFixture,
) -> None:
    mock_issues: list[dict[str, Any]] = [
        {
            "id": 1,
            "html_url": "url1",
            "title": "Issue 1",
            "body": "Body 1",
            "comments": 0,
            "labels": [],
        },
    ]

    mock_request = mocker.patch.object(github_issue_fetcher.client, "request")
    mock_request.return_value = (mock_issues, {})

    issues = [
        issue
        async for issue in github_issue_fetcher.fetch_issues(
            repo_owner="test",
            repo_name="repo",
        )
    ]

    assert len(issues) == 1
    assert isinstance(issues[0], GithubIssue)
    assert issues[0].id == "1"
    assert issues[0].title == "Issue 1"
    assert issues[0].body == "Body 1"
    assert len(issues[0].comments) == 0


async def test_fetch_issues_with_comments(
    github_issue_fetcher: GitHubIssuesFetcher,
    mocker: MockerFixture,
) -> None:
    mock_issue: dict[str, Any] = {
        "id": 1,
        "html_url": "url1",
        "title": "Issue 1",
        "body": "Body 1",
        "comments": 1,
        "comments_url": "https://api.github.com/repos/test/repo/issues/1/comments",
        "labels": [],
    }

    mock_comment: dict[str, Any] = {
        "id": 100,
        "html_url": "comment_url1",
        "body": "Comment 1",
    }

    mock_request = mocker.patch.object(github_issue_fetcher.client, "request")
    mock_request.side_effect = [
        ([mock_issue], {}),
        ([mock_comment], {}),
    ]

    issues = [
        issue
        async for issue in github_issue_fetcher.fetch_issues(
            repo_owner="test",
            repo_name="repo",
        )
    ]

    assert len(issues) == 1
    assert len(issues[0].comments) == 1
    assert issues[0].id == "1"
    assert issues[0].title == "Issue 1"
    assert issues[0].comments[0].id == "100"
    assert issues[0].comments[0].body == "Comment 1"


async def test_fetch_issues_with_label_filtering(
    github_issue_fetcher: GitHubIssuesFetcher,
    mocker: MockerFixture,
) -> None:
    mock_issues: list[dict[str, Any]] = [
        {
            "id": 1,
            "html_url": "url1",
            "title": "Issue 1",
            "body": "Body 1",
            "comments": 0,
            "labels": [{"name": "bug"}],
        },
        {
            "id": 2,
            "html_url": "url2",
            "title": "Issue 2",
            "body": "Body 2",
            "comments": 0,
            "labels": [{"name": "feature"}],
        },
    ]

    mock_request = mocker.patch.object(github_issue_fetcher.client, "request")
    mock_request.return_value = (mock_issues, {})

    # Test include_labels
    issues = [
        issue
        async for issue in github_issue_fetcher.fetch_issues(
            repo_owner="test",
            repo_name="repo",
            include_labels=["bug"],
        )
    ]
    assert len(issues) == 1
    assert issues[0].id == "1"

    # Test exclude_labels
    issues = [
        issue
        async for issue in github_issue_fetcher.fetch_issues(
            repo_owner="test",
            repo_name="repo",
            exclude_labels=["bug"],
        )
    ]
    assert len(issues) == 1
    assert issues[0].id == "2"


async def test_fetch_issues_with_issue_age_limit(
    github_issue_fetcher: GitHubIssuesFetcher,
    mocker: MockerFixture,
) -> None:
    mock_request = mocker.patch.object(github_issue_fetcher.client, "request")
    mock_request.return_value = ([], {})

    _ = [
        issue
        async for issue in github_issue_fetcher.fetch_issues(
            repo_owner="test",
            repo_name="repo",
            issue_age_limit=30,
        )
    ]

    # Verify that the since parameter was included in the request
    call_args = mock_request.call_args
    assert call_args is not None
    _, kwargs = call_args
    params = kwargs.get("params", {})
    assert "since" in params
    # Verify the since parameter is a date 30 days ago
    cutoff_date = datetime.now() - timedelta(days=30)
    assert params["since"] == cutoff_date.strftime("%Y-%m-%d")


async def test_fetch_issues_skip_pull_requests(
    github_issue_fetcher: GitHubIssuesFetcher,
    mocker: MockerFixture,
) -> None:
    mock_issues: list[dict[str, Any]] = [
        {
            "id": 1,
            "html_url": "url1",
            "title": "Issue 1",
            "body": "Body 1",
            "comments": 0,
            "labels": [],
        },
        {
            "id": 2,
            "html_url": "url2",
            "title": "PR 1",
            "body": "Body 2",
            "comments": 0,
            "labels": [],
            "pull_request": {"url": "pr_url"},
        },
    ]

    mock_request = mocker.patch.object(github_issue_fetcher.client, "request")
    mock_request.return_value = (mock_issues, {})

    issues = [
        issue
        async for issue in github_issue_fetcher.fetch_issues(
            repo_owner="test",
            repo_name="repo",
        )
    ]

    assert len(issues) == 1
    assert issues[0].id == "1"
    assert issues[0].title == "Issue 1"


async def test_fetch_issues_multiple_pages(
    github_issue_fetcher: GitHubIssuesFetcher,
    mocker: MockerFixture,
) -> None:
    mock_responses: list[tuple[list[dict[str, Any]], dict[str, str]]] = [
        # First page with 1 issue and a link to the next page
        (
            [
                {
                    "id": 1,
                    "html_url": "url1",
                    "title": "Issue 1",
                    "body": "Body 1",
                    "comments": 0,
                    "labels": [],
                }
            ],
            {
                "Link": '<https://api.github.com/repos/test/repo/issues?page=2&per_page=100&state=all&sort=updated&direction=desc>; rel="next"'
            },
        ),
        (
            [
                {
                    "id": 2,
                    "html_url": "url2",
                    "title": "Issue 2",
                    "body": "Body 2",
                    "comments": 0,
                    "labels": [],
                }
            ],
            {},
        ),
    ]

    mock_request = mocker.patch.object(github_issue_fetcher.client, "request")
    mock_request.side_effect = mock_responses

    issues = [
        issue
        async for issue in github_issue_fetcher.fetch_issues(
            repo_owner="test",
            repo_name="repo",
        )
    ]

    assert len(issues) == 2
    assert issues[0].id == "1"
    assert issues[1].id == "2"
    mock_request.assert_has_calls(
        [
            call(
                "GET",
                "https://api.github.com/repos/test/repo/issues",
                params={
                    "per_page": "100",
                    "state": "all",
                    "sort": "updated",
                    "direction": "desc",
                },
            ),
            # All subsequent requests don't need params as they are included in the URL from the Link header
            call(
                "GET",
                "https://api.github.com/repos/test/repo/issues?page=2&per_page=100&state=all&sort=updated&direction=desc",
                params=None,
            ),
        ]
    )
