import json
from openai import APIError, OpenAI, pydantic_function_tool
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionMessageToolCall,
)

from src.chat.exceptions import ChatException
from src.chat.prompts import get_system_prompt
from src.chat.schemas import ChatResponse, CreateChatInput
from src.chat.tools import ToolDefinition
from src.common.exceptions import (
    KnownException,
    ResourceNotFoundException,
    ResourceType,
)
from src.common.schemas import Document
from src.sources.schemas import SearchSourceInput, SourceMetadata
from src.sources.service import SourceService


class ChatService:
    def __init__(
        self,
        *,
        source_service: SourceService,
        openai_client: OpenAI,
        base_system_prompt: str,
        tool_definitions: list[ToolDefinition],
        chat_history_limit: int,
    ):
        self.chat_client = openai_client
        self.source_service = source_service
        self.base_system_prompt = base_system_prompt
        self.chat_history_limit = chat_history_limit
        self.tools = [
            pydantic_function_tool(
                model=tool.model,
                name=tool.name,
                description=tool.description,
            )
            for tool in tool_definitions
        ]

    def _get_sources(
        self, source_names: list[str] | None = None
    ) -> list[SourceMetadata]:
        """Retrieve and validate sources."""
        if not source_names:
            sources = self.source_service.list_sources()
        else:
            sources = [self.source_service.get_source(name) for name in source_names]

        if not sources:
            raise ChatException("No sources found.")

        return sources

    def _create_chat_messages(
        self,
        system_prompt: str,
        chat_history: list[ChatCompletionMessageParam],
        user_message: str,
    ) -> list[ChatCompletionMessageParam]:
        """Create the complete list of chat messages."""
        return [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt),
            *chat_history,
            ChatCompletionUserMessageParam(role="user", content=user_message),
        ]

    def _handle_tool_call(
        self,
        tool_call: ChatCompletionMessageToolCall,
    ) -> tuple[ChatCompletionToolMessageParam, list[Document]]:
        """Handle a tool call and append the result to messages."""
        if tool_call.function.name != "search_source":
            raise ValueError(f"Unknown tool call: {tool_call.function.name}")

        args = json.loads(tool_call.function.arguments)
        documents = self.source_service.search_source(SearchSourceInput(**args))
        content = json.dumps(
            [{"url": doc.url, "content": doc.content} for doc in documents]
        )

        return ChatCompletionToolMessageParam(
            tool_call_id=tool_call.id,
            content=content,
            role="tool",
        ), documents

    def generate_response(self, chat_input: CreateChatInput) -> ChatResponse:
        """Generate a response based on chat input."""
        try:
            # Initialize chat context
            sources = self._get_sources(chat_input.sources)
            system_prompt = get_system_prompt(
                self.base_system_prompt, sources, chat_input.max_attempts
            )

            # Prepare chat history
            chat_history: list[ChatCompletionMessageParam] = [
                (
                    ChatCompletionUserMessageParam(role="user", content=msg.content)
                    if msg.role == "user"
                    else ChatCompletionAssistantMessageParam(
                        role="assistant", content=msg.content
                    )
                )
                for msg in chat_input.messages[-self.chat_history_limit : -1]
            ]

            messages = self._create_chat_messages(
                system_prompt, chat_history, chat_input.messages[-1].content
            )

            retrieved_documents: list[Document] = []

            # Generate response with retry logic
            for _ in range(chat_input.max_attempts):
                response = self.chat_client.chat.completions.create(
                    model=chat_input.chat_model,
                    messages=messages,
                    tools=self.tools,
                )

                message = response.choices[0].message
                messages.append(message)  # type: ignore

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_response, docs = self._handle_tool_call(tool_call)
                        messages.append(tool_response)
                        retrieved_documents.extend(docs)
                elif message.content:
                    return ChatResponse(
                        message=message.content, retrieved_documents=retrieved_documents
                    )
                else:
                    raise ValueError(
                        "No response content or tool call found in completion."
                    )

            return ChatResponse(
                message="I'm sorry, but I don't have the information you're looking for.",
                retrieved_documents=retrieved_documents,
            )

        except ChatException as e:
            raise KnownException(str(e))
        except APIError as e:
            if e.code == "model_not_found":
                raise ResourceNotFoundException(
                    ResourceType.MODEL, chat_input.chat_model
                )
            raise e
