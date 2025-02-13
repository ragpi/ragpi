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
from src.chat.schemas import ChatResponse, CreateChatRequest
from src.chat.tools.definitions import ToolDefinition
from src.chat.tools.schamas import RetrieveDocuments
from src.common.exceptions import KnownException
from src.llm_providers.exceptions import handle_openai_client_error
from src.sources.metadata.schemas import SourceMetadata
from src.sources.service import SourceService


class ChatService:
    def __init__(
        self,
        *,
        source_service: SourceService,
        openai_client: OpenAI,
        project_name: str,
        project_description: str,
        base_system_prompt: str,
        tool_definitions: list[ToolDefinition],
        chat_history_limit: int,
        max_iterations: int,
        retrieval_top_k: int,
    ):
        self.chat_client = openai_client
        self.source_service = source_service
        self.project_name = project_name
        self.project_description = project_description
        self.base_system_prompt = base_system_prompt
        self.chat_history_limit = chat_history_limit
        self.max_iterations = max_iterations
        self.retrieval_top_k = retrieval_top_k
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
    ) -> ChatCompletionToolMessageParam:
        """Handle a tool call and append the result to messages."""
        if tool_call.function.name != "retrieve_documents":
            raise ValueError(f"Unknown tool call: {tool_call.function.name}")

        args = json.loads(tool_call.function.arguments)
        source_input = RetrieveDocuments(**args)
        documents = self.source_service.search_source(
            source_name=source_input.source_name,
            semantic_query=source_input.semantic_query,
            full_text_query=source_input.full_text_query,
            top_k=self.retrieval_top_k,
        )

        content = json.dumps(
            [{"url": doc.url, "content": doc.content} for doc in documents]
        )

        return ChatCompletionToolMessageParam(
            tool_call_id=tool_call.id,
            content=content,
            role="tool",
        )

    def generate_response(self, chat_input: CreateChatRequest) -> ChatResponse:
        """Generate a response based on chat input."""
        try:
            # Initialize chat context
            sources = self._get_sources(chat_input.sources)
            system_prompt = get_system_prompt(
                project_name=self.project_name,
                project_description=self.project_description,
                base_prompt=self.base_system_prompt,
                sources=sources,
                max_attempts=self.max_iterations,
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

            # Generate response
            for _ in range(self.max_iterations):
                response = self.chat_client.chat.completions.create(
                    model=chat_input.model,
                    messages=messages,
                    tools=self.tools,
                )

                message = response.choices[0].message
                messages.append(message)  # type: ignore

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_response = self._handle_tool_call(tool_call)
                        messages.append(tool_response)
                elif message.content:
                    return ChatResponse(message=message.content)
                else:
                    raise ValueError(
                        "No response content or tool call found in completion."
                    )

            return ChatResponse(
                message="I'm sorry, but I don't have the information you're looking for."
            )

        except ChatException as e:
            raise KnownException(str(e))
        except APIError as e:
            handle_openai_client_error(e, chat_input.model)
            raise e
