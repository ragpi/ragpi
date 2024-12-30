import pytest
from pytest_mock import MockerFixture
from openai import APIError, OpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import Function

from src.chat.service import ChatService
from src.chat.schemas import ChatMessage, ChatResponse, CreateChatInput
from src.common.exceptions import ResourceNotFoundException, ResourceType
from src.common.schemas import Document
from src.source.service import SourceService
from src.source.schemas import SearchSourceInput


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(
            id="1",
            url="test.com",
            title="Test title 1",
            content="Test content 1",
            created_at="2024-01-01T00:00:00",
        ),
        Document(
            id="2",
            url="test.com",
            title="Test title 2",
            content="Test content 2",
            created_at="2024-01-01T00:00:00",
        ),
    ]


@pytest.fixture
def mock_source_service(mocker: MockerFixture) -> SourceService:
    return mocker.Mock(spec=SourceService)


@pytest.fixture
def mock_openai_client(mocker: MockerFixture) -> OpenAI:
    client = mocker.Mock(spec=OpenAI)
    client.chat = mocker.Mock()
    client.chat.completions = mocker.Mock()
    return client


@pytest.fixture
def chat_service(
    mock_source_service: SourceService,
    mock_openai_client: OpenAI,
) -> ChatService:
    return ChatService(
        source_service=mock_source_service,
        openai_client=mock_openai_client,
        base_system_prompt="You are a helpful assistant.",
        chat_history_limit=10,
    )


@pytest.fixture
def sample_chat_input() -> CreateChatInput:
    return CreateChatInput(
        messages=[
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
            ChatMessage(role="user", content="What is the weather?"),
        ],
        chat_model="test-model",
        sources=["source1", "source2"],
        max_attempts=3,
    )


def test_generate_response_direct_answer(
    chat_service: ChatService,
    mock_openai_client: OpenAI,
    sample_chat_input: CreateChatInput,
    mocker: MockerFixture,
) -> None:
    mock_completion = ChatCompletion(
        id="test-id",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content="This is a direct answer",
                    role="assistant",
                ),
            )
        ],
        created=1234567890,
        model="gpt-4",
        object="chat.completion",
    )
    mock_create_completion = mocker.patch.object(
        mock_openai_client.chat.completions,
        "create",
        return_value=mock_completion,
    )

    response = chat_service.generate_response(sample_chat_input)

    assert isinstance(response, ChatResponse)
    assert response.message == "This is a direct answer"
    mock_create_completion.assert_called_once()


def test_generate_response_with_tool_calls(
    chat_service: ChatService,
    mock_openai_client: OpenAI,
    mock_source_service: SourceService,
    sample_chat_input: CreateChatInput,
    sample_documents: list[Document],
    mocker: MockerFixture,
) -> None:
    # Mock first response with tool call
    tool_call_completion = ChatCompletion(
        id="test-id-1",
        choices=[
            Choice(
                finish_reason="tool_calls",
                index=0,
                message=ChatCompletionMessage(
                    content=None,
                    role="assistant",
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id="call-1",
                            type="function",
                            function=Function(
                                name="search_source",
                                arguments='{"query": "test query", "name": "source1", "top_k": 3}',
                            ),
                        )
                    ],
                ),
            )
        ],
        created=1234567890,
        model="gpt-4",
        object="chat.completion",
    )

    # Mock final response with answer
    final_completion = ChatCompletion(
        id="test-id-2",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content="Here is the answer based on the search",
                    role="assistant",
                ),
            )
        ],
        created=1234567890,
        model="gpt-4",
        object="chat.completion",
    )

    mock_create_completion = mocker.patch.object(
        mock_openai_client.chat.completions,
        "create",
        side_effect=[tool_call_completion, final_completion],
    )

    # Mock source service search results
    mock_search_source = mocker.patch.object(
        mock_source_service,
        "search_source",
        return_value=sample_documents,
    )

    response = chat_service.generate_response(sample_chat_input)

    assert isinstance(response, ChatResponse)
    assert response.message == "Here is the answer based on the search"
    assert mock_create_completion.call_count == 2
    mock_search_source.assert_called_once_with(
        SearchSourceInput(query="test query", name="source1", top_k=3)
    )


def test_generate_response_max_attempts_exceeded(
    chat_service: ChatService,
    mock_openai_client: OpenAI,
    mock_source_service: SourceService,
    sample_chat_input: CreateChatInput,
    sample_documents: list[Document],
    mocker: MockerFixture,
) -> None:
    # Mock tool call response that keeps searching
    tool_call_completion = ChatCompletion(
        id="test-id",
        choices=[
            Choice(
                finish_reason="tool_calls",
                index=0,
                message=ChatCompletionMessage(
                    content=None,
                    role="assistant",
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id="call-1",
                            type="function",
                            function=Function(
                                name="search_source",
                                arguments='{"query": "test query", "name": "source1", "top_k": 3}',
                            ),
                        )
                    ],
                ),
            )
        ],
        created=1234567890,
        model="gpt-4",
        object="chat.completion",
    )

    mock_create_completion = mocker.patch.object(
        mock_openai_client.chat.completions,
        "create",
        return_value=tool_call_completion,
    )

    # Mock source service search results
    mocker.patch.object(
        mock_source_service,
        "search_source",
        return_value=sample_documents,
    )

    response = chat_service.generate_response(sample_chat_input)

    assert isinstance(response, ChatResponse)
    assert (
        response.message
        == "I'm sorry, but I don't have the information you're looking for."
    )
    assert mock_create_completion.call_count == sample_chat_input.max_attempts


def test_generate_response_model_not_found(
    chat_service: ChatService,
    mock_openai_client: OpenAI,
    sample_chat_input: CreateChatInput,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        mock_openai_client.chat.completions,
        "create",
        side_effect=APIError(
            request=mocker.Mock(),
            message="Model not found",
            body={"code": "model_not_found", "param": "model", "type": "not_found"},
        ),
    )

    with pytest.raises(ResourceNotFoundException) as exc_info:
        chat_service.generate_response(sample_chat_input)

    assert exc_info.value.resource_type == ResourceType.MODEL
    assert exc_info.value.identifier == sample_chat_input.chat_model
