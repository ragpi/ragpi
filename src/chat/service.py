import json
from openai import OpenAI, pydantic_function_tool
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
)

from src.chat.schemas import ChatResponse, CreateChatInput
from src.chat.tools import FUNCTION_TOOLS
from src.config import settings
from src.source.schemas import SearchSourceInput
from src.source.service import SourceService


class ChatService:
    def __init__(self):
        self.openai_client = OpenAI()
        self.default_chat_model = settings.CHAT_MODEL
        self.base_system_prompt = settings.BASE_SYSTEM_PROMPT
        self.tools = [
            pydantic_function_tool(
                model=tool.model,
                name=tool.name,
                description=tool.description,
            )
            for tool in FUNCTION_TOOLS
        ]
        self.source_service = SourceService()

    def _create_system_prompt(self, chat_input: CreateChatInput) -> str:
        sources = [self.source_service.get_source(name) for name in chat_input.sources]

        sources_info = [
            {
                "name": source.name,
                "description": source.description,
            }
            for source in sources
        ]

        return f"""
{self.base_system_prompt}

Utilize the `search_source` tool to find relevant information from the available sources.

**Available Sources:**
{sources_info}

**Guidelines:**
1. **Relevance:** 
    - Always prioritize the most relevant sources when addressing the user's query.
2. **Search Strategy:** 
    - If initial searches do not yield sufficient information, expand the search by increasing the search top_k or refining the search query.
3. **Attempts:**
    - You have {chat_input.max_attempts} attempts to answer the user's question.
4. **Providing Information:**
    - When relevant information is found, include links to the source documents in your response.
    - If unable to find an answer after exhausting all attempts, respond with: "I'm sorry, but I don't have the information you're looking for."
"""

    def generate_response(self, chat_input: CreateChatInput) -> ChatResponse:
        system_prompt = self._create_system_prompt(chat_input)

        chat_history = chat_input.messages[:-1]

        previous_messages = [
            (
                ChatCompletionUserMessageParam(role="user", content=message.content)
                if message.role == "user"
                else ChatCompletionAssistantMessageParam(
                    role="assistant", content=message.content
                )
            )
            for message in chat_history
        ]

        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt),
            *previous_messages,
            ChatCompletionUserMessageParam(
                role="user", content=chat_input.messages[-1].content
            ),
        ]

        attempts = 0
        while attempts < chat_input.max_attempts:
            response = self.openai_client.chat.completions.create(
                model=chat_input.chat_model or self.default_chat_model,
                messages=messages,
                tools=self.tools,
            )

            message = response.choices[0].message

            messages.append(message)  # type: ignore

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "search_source":
                        args = json.loads(tool_call.function.arguments)
                        documents = self.source_service.search_source(
                            SearchSourceInput(**args)
                        )
                        content = json.dumps(
                            [
                                {
                                    "url": doc.url,
                                    "content": doc.content,
                                }
                                for doc in documents
                            ]
                        )
                        messages.append(
                            ChatCompletionToolMessageParam(
                                tool_call_id=tool_call.id,
                                content=content,
                                role="tool",
                            )
                        )
                    else:
                        raise ValueError(
                            f"Unknown tool call: {tool_call.function.name}"
                        )
            elif message.content:
                return ChatResponse(message=message.content)
            else:
                raise ValueError(
                    "No response content or tool call found in completion."
                )

            attempts += 1

        return ChatResponse(
            message="I'm sorry, but I don't have the information you're looking for.",
        )
