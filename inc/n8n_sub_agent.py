
from __future__ import annotations
import logging
import os
import json
import aiohttp
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union, Tuple
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)
import re
# from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    metrics,
)
from livekit.agents.job import get_current_job_context
from livekit.agents.llm import LLM
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero
from livekit.agents import APIConnectionError, APIStatusError, APITimeoutError, llm
from livekit.agents.llm import ToolChoice, utils as llm_utils
from livekit.agents.llm.chat_context import ChatContext
from livekit.agents.llm.tool_context import FunctionTool
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)
import uuid
from livekit.agents.utils import is_given
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletionToolChoiceOptionParam,
    completion_create_params,
)
from openai.types.chat.chat_completion_chunk import Choice
import httpx
from dotenv import load_dotenv, find_dotenv, dotenv_values
from inc.share_data import SharedData

logger = logging.getLogger("multi-agent-system")


class N8NSubAgent(Agent):
    """
    Specialized agent that acts as a proxy to an external API endpoint.
    """

    def __init__(
        self,
        api_url: str = None,
        *,
        chat_ctx: Optional[ChatContext] = None,
        sessionId: str = None,
        agent_id: str = None,
        context: RunContext[SharedData] = None,
        query: str = ""
    ) -> None:
        super().__init__(
            instructions=(
                f""
            ),
            chat_ctx=chat_ctx,
        )
        self.query = query
        self.sessionId = sessionId
        self.api_url = api_url
        self.agent_id = agent_id
        self._client = httpx.AsyncClient(
            timeout = httpx.Timeout(connect=15.0, read=5.0, write=5.0, pool=5.0),
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=50,
                keepalive_expiry=120,
            ),
        )

    async def on_enter(self):
        """Called when the agent is added to the session."""
        logger.info("N8NSubAgent agent started")
        self.session.generate_reply(
            instructions=f"{self.query}"
        )



    async def llm_node(self, chat_ctx, tools, model_settings):
        retryable = True
        
        try:
            # Prepare the request payload according to your endpoint's format
            payload = self._prepare_payload(chat_ctx)
            logger.info(f"Sending request to API: {payload}")
            if payload is None:
                return
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            # if self._api_key:
            #     headers["X-N8N-API-KEY"] = self._llm.api_key
            # self.headers = {"X-N8N-API-KEY": api_key} if api_key else {}
            # Make the request to your endpoint
            response = await self._client.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=DEFAULT_API_CONNECT_OPTIONS.timeout,
            )
            
            # Check for errors
            if response.status_code != 200:
                raise APIStatusError(
                    f"API request failed with status {response.status_code}",
                    status_code=response.status_code,
                    body=response.text,
                    retryable=retryable,
                )
                
            # Parse the response
            data = response.json()
            logger.info(f"Received response from API: {data}")
            # Convert the response to the expected format
            chat_chunk = self._parse_response(data)
            yield chat_chunk
            
        except httpx.TimeoutException:
            raise APITimeoutError(retryable=retryable) from None
        except httpx.HTTPStatusError as e:
            raise APIStatusError(
                str(e),
                status_code=e.response.status_code,
                retryable=retryable,
            ) from None
        except Exception as e:
            raise APIConnectionError(retryable=retryable) from e
        
        
    def _prepare_payload(self, chat_ctx: ChatContext) -> dict:
        """
        Convert the chat context into your endpoint's expected format.
        """
        # Get the last message from the chat context
        # loop over the chat context items in reverse order and find the first message that is not from the assistant
        text_content = ""
        for item in reversed(chat_ctx.items):
            logger.info(f"Chat context item: {item}")
            if item.role == "assistant":
                logger.info(f"Chat context item role: {item.role}")
                break
            if item.role != "assistant" and item.content  and isinstance(item.content[0], str):
                for content in item.content:
                    if isinstance(content, str):
                        if text_content:
                            text_content += "\n"
                        text_content += content
                if(text_content == ""):
                    continue
                break
        if(text_content == ""):
            return None
        logger.info(f"Last message: {text_content}")
        userdata: SharedData = self.session.userdata
        return {
            "sessionId": self.sessionId,
            "eventSessionId": userdata.eventSessionId,
            "action": "sendMessage",
            "chatInput": text_content,
        }


    def _parse_response(self, data: dict) -> llm.ChatChunk:
        """
        Convert your endpoint's response format to the standard ChatChunk format.
        """
        output = data.get("output", "")
        logger.info(f"tools: {self.tools}")
        # Check for STATUS_OF_TASK in the output
        status_match = re.search(r'STATUS_OF_TASK=(\w+)', output)
        status = status_match.group(1) if status_match else None
        clean_output = re.sub(r'\s*STATUS_OF_TASK=\w+', '', output).strip()
        
        # Prepare tool calls if status is COMPLETED
        tool_calls = []
        if status == "COMPLETED":
            tool_calls.append(
                llm.FunctionToolCall(
                    name="task_completed",
                    arguments="",
                    call_id="task_completed_" + str(uuid.uuid4()),
                )
            )
            userdata: SharedData = self.session.userdata
            userdata.coordinator_agent._chat_ctx.add_message(
                role=f"assistant",
                content=f"response from agent {self.agent_id}: {clean_output}",
            )
        
        return llm.ChatChunk(
            id=str(uuid.uuid4()),
            delta=llm.ChoiceDelta(
                content=clean_output,
                role="assistant",
                tool_calls=tool_calls,
            ),
        )

    @function_tool
    async def task_completed(
        self,
        context: RunContext[SharedData],
    ):
        """
        Return control to the coordinator agent when the task is complete.
        
        """
        # # context.userdata.current_agent = "coordinator"
        # from inc.coordinator_agent import CoordinatorAgent
        # # Create a new coordinator agent
        # coordinator = CoordinatorAgent(instructions="",chat_ctx= context.userdata.chat_context)

        return context.userdata.coordinator_agent

