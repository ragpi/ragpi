import datetime
import pytest
from aiohttp import ClientError, ClientResponse, ClientSession
from pytest_mock import MockerFixture

from src.connectors.exceptions import ConnectorException
from src.connectors.common.github_client import GitHubClient


async def test_github_client_initialization() -> None:
    # Test successful initialization
    client = GitHubClient(
        concurrent_requests=2,
        user_agent="test-agent",
        github_api_version="2022-11-28",
        github_token="test-token",
    )
    assert isinstance(client.session, ClientSession)
    assert client.semaphore._value == 2
    await client.session.close()

    # Test initialization without token
    with pytest.raises(ConnectorException, match="GITHUB_TOKEN is required"):
        GitHubClient(
            concurrent_requests=2,
            user_agent="test-agent",
            github_api_version="2022-11-28",
            github_token="",
        )


async def test_parse_link_header(github_client: GitHubClient) -> None:
    # Test with valid header
    test_header = '<https://api.github.com/search?page=2>; rel="next", <https://api.github.com/search?page=5>; rel="last"'
    expected = {
        "next": "https://api.github.com/search?page=2",
        "last": "https://api.github.com/search?page=5",
    }
    result = github_client.parse_link_header(test_header)  # type: ignore
    assert result == expected

    # Test with invalid header
    invalid_header = "invalid header format"
    result = github_client.parse_link_header(invalid_header)  # type: ignore
    assert result == {}


async def test_request_success(
    github_client: GitHubClient, mocker: MockerFixture
) -> None:
    mock_response = mocker.Mock(spec=ClientResponse)
    mock_response.status = 200
    mock_response.json.return_value = {"key": "value"}
    mock_response.headers = {"header": "value"}

    mock_session = mocker.patch.object(github_client.session, "request")
    mock_session.return_value.__aenter__.return_value = mock_response

    data, headers = await github_client.request("GET", "https://api.github.com/test")
    assert data == {"key": "value"}
    assert headers == {"header": "value"}


async def test_request_rate_limit(
    github_client: GitHubClient, mocker: MockerFixture
) -> None:
    # Mock responses for rate limit
    rate_limit_response = mocker.Mock(spec=ClientResponse)
    rate_limit_response.status = 429
    rate_limit_response.headers = {
        "Retry-After": "1",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(datetime.datetime.now().timestamp() + 1),
    }

    # Mock response for successful request
    success_response = mocker.Mock(spec=ClientResponse)
    success_response.status = 200
    success_response.json.return_value = {"key": "value"}
    success_response.headers = {"X-RateLimit-Remaining": "100"}
    mock_session = mocker.patch.object(github_client.session, "request")
    mock_session.return_value.__aenter__.side_effect = [
        rate_limit_response,
        success_response,
    ]

    data, _ = await github_client.request("GET", "https://api.github.com/test")
    assert data == {"key": "value"}
    assert mock_session.call_count == 2


async def test_request_404(github_client: GitHubClient, mocker: MockerFixture) -> None:
    mock_response = mocker.Mock(spec=ClientResponse)
    mock_response.status = 404

    mock_session = mocker.patch.object(github_client.session, "request")
    mock_session.return_value.__aenter__.return_value = mock_response

    with pytest.raises(
        ConnectorException,
        match="Resource not found at https://api.github.com/test",
    ):
        await github_client.request("GET", "https://api.github.com/test")


async def test_request_401(github_client: GitHubClient, mocker: MockerFixture) -> None:
    mock_response = mocker.Mock(spec=ClientResponse)
    mock_response.status = 401

    mock_session = mocker.patch.object(github_client.session, "request")
    mock_session.return_value.__aenter__.return_value = mock_response

    with pytest.raises(ConnectorException, match="GITHUB_TOKEN is not authorized"):
        await github_client.request("GET", "https://api.github.com/test")


async def test_request_client_error(
    github_client: GitHubClient, mocker: MockerFixture
) -> None:
    mock_session = mocker.patch.object(github_client.session, "request")
    mock_session.return_value.__aenter__.side_effect = ClientError()

    data, headers = await github_client.request(
        "GET", "https://api.github.com/test", max_attempts=3, retry_backoff=0.05
    )
    assert data is None
    assert headers is None
    assert mock_session.call_count == 3  # initial request + 2 retries


async def test_request_unexpected_error(
    github_client: GitHubClient, mocker: MockerFixture
) -> None:
    mock_session = mocker.patch.object(github_client.session, "request")
    mock_session.return_value.__aenter__.side_effect = Exception("Unexpected error")

    with pytest.raises(ConnectorException, match="Unexpected error"):
        await github_client.request("GET", "https://api.github.com/test")
