import json
from typing import cast

from groq import Groq
from groq.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import build_tool_definitions, execute_tool
from app.tools.knowledge import KnowledgeTool

from app.agent.context import AgentContext
from app.observability.events import SupportEvent
from app.observability.logger import log_event


MAX_TOOL_ITERATIONS = 5


class SupportAgent:
    def __init__(
        self,
        client: Groq,
        model: str,
        knowledge_tool: KnowledgeTool,
    ):
        self.client = client
        self.model = model
        self.knowledge_tool = knowledge_tool

    def chat(
        self,
        message: str,
        context: AgentContext,
    ) -> str:

        customer_id = context.customer_id
        request_id = context.request_id

        log_event(
            SupportEvent(
                event_type="agent_request",
                request_id=request_id,
                customer_id=customer_id,
                function_name="chat",
                details={
                    "message_length": len(message),
                },
            )
        )

        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": message,
            },
        ]

        tools = cast(
            list[ChatCompletionToolParam],
            build_tool_definitions(),
        )

        # Tracks tool name + exact arguments so the agent cannot
        # repeatedly execute the same operation.
        tool_call_history: set[tuple[str, str]] = set()

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message

            messages.append(
                cast(
                    ChatCompletionMessageParam,
                    assistant_message,
                )
            )

            if not assistant_message.tool_calls:
                final_response = assistant_message.content or ""

                log_event(
                    SupportEvent(
                        event_type="agent_response",
                        request_id=request_id,
                        customer_id=customer_id,
                        function_name="chat",
                        details={
                            "response_length": len(final_response),
                            "iteration": iteration + 1,
                        },
                    )
                )

                return final_response

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                raw_arguments = tool_call.function.arguments

                log_event(
                    SupportEvent(
                        event_type="tool_call",
                        request_id=request_id,
                        customer_id=customer_id,
                        function_name="execute_tool",
                        details={
                            "tool_name": tool_name,
                            "iteration": iteration + 1,
                        },
                    )
                )

                tool_success = True

                try:
                    arguments = json.loads(raw_arguments)

                    if not isinstance(arguments, dict):
                        raise ValueError(
                            "Tool arguments must be a JSON object."
                        )

                except (json.JSONDecodeError, ValueError):
                    tool_success = False

                    tool_result = json.dumps(
                        {
                            "error": "Invalid tool arguments.",
                        }
                    )

                else:
                    # Use the raw JSON arguments as part of the identity
                    # of the tool call. This lets us detect an identical
                    # tool invocation without making assumptions about
                    # the structure of individual tools.
                    tool_key = (
                        tool_name,
                        raw_arguments,
                    )

                    if tool_key in tool_call_history:
                        tool_success = False

                        tool_result = json.dumps(
                            {
                                "error": (
                                    "This exact tool request has already "
                                    "been executed. Do not repeat the "
                                    "same request. Use the existing result "
                                    "or choose another appropriate action."
                                )
                            }
                        )

                        log_event(
                            SupportEvent(
                                event_type="tool_repeat_blocked",
                                request_id=request_id,
                                customer_id=customer_id,
                                function_name="execute_tool",
                                level="warning",
                                success=False,
                                details={
                                    "tool_name": tool_name,
                                    "iteration": iteration + 1,
                                },
                            )
                        )

                    else:
                        tool_call_history.add(tool_key)

                        tool_result = execute_tool(
                            tool_name=tool_name,
                            arguments=arguments,
                            customer_id=customer_id,
                            knowledge_tool=self.knowledge_tool,
                        )

                log_event(
                    SupportEvent(
                        event_type="tool_result",
                        request_id=request_id,
                        customer_id=customer_id,
                        function_name="execute_tool",
                        success=tool_success,
                        details={
                            "tool_name": tool_name,
                        },
                    )
                )

                messages.append(
                    cast(
                        ChatCompletionMessageParam,
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result,
                        },
                    )
                )

        log_event(
            SupportEvent(
                event_type="agent_iteration_limit",
                request_id=request_id,
                customer_id=customer_id,
                function_name="chat",
                level="warning",
                success=False,
                details={
                    "max_iterations": MAX_TOOL_ITERATIONS,
                },
            )
        )

        return (
            "I'm unable to complete this request safely right now. "
            "Please contact support for assistance."
        )