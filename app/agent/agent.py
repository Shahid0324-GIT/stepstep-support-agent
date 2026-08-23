import json
import time
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

        # Once a knowledge search explicitly reports that no relevant
        # knowledge exists, the agent must not answer the request by
        # inferring a policy from unrelated information.
        knowledge_gap_detected = False

        # Prevents the safety mechanism from repeatedly escalating.
        escalation_requested = False

        for iteration in range(MAX_TOOL_ITERATIONS):
            llm_started = time.perf_counter()

            log_event(
                SupportEvent(
                    event_type="llm_request",
                    request_id=request_id,
                    customer_id=customer_id,
                    function_name="chat",
                    details={
                        "model": self.model,
                        "iteration": iteration + 1,
                        "message_count": len(messages),
                        "tool_count": len(tools),
                    },
                )
            )

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )

            except Exception as exc:
                duration_ms = (
                    time.perf_counter() - llm_started
                ) * 1000

                log_event(
                    SupportEvent(
                        event_type="llm_response",
                        request_id=request_id,
                        customer_id=customer_id,
                        function_name="chat",
                        level="error",
                        success=False,
                        duration_ms=duration_ms,
                        error=str(exc),
                        details={
                            "model": self.model,
                            "iteration": iteration + 1,
                        },
                    )
                )

                return (
                    "I'm unable to complete this request safely right now. "
                    "Please contact support for assistance."
                )

            duration_ms = (
                time.perf_counter() - llm_started
            ) * 1000

            assistant_message = response.choices[0].message

            log_event(
                SupportEvent(
                    event_type="llm_response",
                    request_id=request_id,
                    customer_id=customer_id,
                    function_name="chat",
                    duration_ms=duration_ms,
                    details={
                        "model": self.model,
                        "iteration": iteration + 1,
                        "has_tool_calls": bool(
                            assistant_message.tool_calls
                        ),
                        "tool_call_count": len(
                            assistant_message.tool_calls or []
                        ),
                        "response_length": len(
                            assistant_message.content or ""
                        ),
                    },
                )
            )

            messages.append(
                cast(
                    ChatCompletionMessageParam,
                    assistant_message,
                )
            )

            if not assistant_message.tool_calls:
                final_response = assistant_message.content or ""

                # If the model attempted to answer after a policy
                # knowledge gap without escalating, do not allow that
                # answer to become the final response.
                if knowledge_gap_detected and not escalation_requested:
                    escalation_requested = True

                    log_event(
                        SupportEvent(
                            event_type="knowledge_gap_escalation",
                            request_id=request_id,
                            customer_id=customer_id,
                            function_name="chat",
                            level="warning",
                            details={
                                "reason": (
                                    "Knowledge search returned no "
                                    "applicable information, but the "
                                    "model attempted to answer without "
                                    "escalating."
                                ),
                                "iteration": iteration + 1,
                            },
                        )
                    )

                    # Treat the forced escalation exactly like a normal tool call
                    # so that the escalation is visible in the observability trace.

                    escalation_tool_name = "escalate_to_support"
                    escalation_tool_call_id = f"safety-escalation-{iteration + 1}"

                    log_event(
                        SupportEvent(
                            event_type="tool_call",
                            request_id=request_id,
                            customer_id=customer_id,
                            function_name="execute_tool",
                            details={
                                "tool_name": escalation_tool_name,
                                "iteration": iteration + 1,
                                "forced": True,
                            },
                        )
                    )

                    escalation_started = time.perf_counter()

                    escalation_result = execute_tool(
                        tool_name=escalation_tool_name,
                        arguments={
                            "reason": (
                                "The knowledge base does not contain "
                                "sufficient information to safely resolve "
                                "the customer's request."
                            ),
                            "category": "knowledge_gap",
                        },
                        customer_id=customer_id,
                        knowledge_tool=self.knowledge_tool,
                    )

                    escalation_duration_ms = (
                        time.perf_counter() - escalation_started
                    ) * 1000

                    log_event(
                        SupportEvent(
                            event_type="tool_execution",
                            request_id=request_id,
                            customer_id=customer_id,
                            function_name="execute_tool",
                            duration_ms=escalation_duration_ms,
                            details={
                                "tool_name": escalation_tool_name,
                                "iteration": iteration + 1,
                                "forced": True,
                            },
                        )
                    )

                    log_event(
                        SupportEvent(
                            event_type="tool_result",
                            request_id=request_id,
                            customer_id=customer_id,
                            function_name="execute_tool",
                            success=True,
                            details={
                                "tool_name": escalation_tool_name,
                                "iteration": iteration + 1,
                                "forced": True,
                            },
                        )
                    )

                    messages.append(
                        cast(
                            ChatCompletionMessageParam,
                            {
                                "role": "tool",
                                "tool_call_id": escalation_tool_call_id,
                                "name": escalation_tool_name,
                                "content": escalation_result,
                            },
                        )
                    )

                    continue

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

                        tool_started = time.perf_counter()

                        tool_result = execute_tool(
                            tool_name=tool_name,
                            arguments=arguments,
                            customer_id=customer_id,
                            knowledge_tool=self.knowledge_tool,
                        )

                        tool_duration_ms = (
                            time.perf_counter() - tool_started
                        ) * 1000

                        # A successful knowledge search can still report
                        # that no applicable knowledge was found.
                        if tool_name == "search_knowledge":
                            try:
                                knowledge_result = json.loads(
                                    tool_result
                                )

                                if (
                                    isinstance(knowledge_result, dict)
                                    and knowledge_result.get("found")
                                    is False
                                ):
                                    knowledge_gap_detected = True

                                    log_event(
                                        SupportEvent(
                                            event_type="knowledge_gap_detected",
                                            request_id=request_id,
                                            customer_id=customer_id,
                                            function_name="execute_tool",
                                            level="warning",
                                            details={
                                                "tool_name": tool_name,
                                                "iteration": iteration + 1,
                                            },
                                        )
                                    )

                            except json.JSONDecodeError:
                                pass

                        log_event(
                            SupportEvent(
                                event_type="tool_execution",
                                request_id=request_id,
                                customer_id=customer_id,
                                function_name="execute_tool",
                                duration_ms=tool_duration_ms,
                                details={
                                    "tool_name": tool_name,
                                    "iteration": iteration + 1,
                                },
                            )
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
                            "iteration": iteration + 1,
                        },
                    )
                )

                # If the model explicitly requested escalation, remember
                # that the knowledge-gap safety guard has been satisfied.
                if tool_name == "escalate_to_support":
                    escalation_requested = True

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