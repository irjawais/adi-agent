
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from livekit.agents.types import (  
    NOT_GIVEN
)
# from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    ChatContext,
    RunContext,
    function_tool,
)
from livekit.agents.llm.chat_context import ChatContext

import uuid

from inc.config import N8N_BASE_URL
from inc.coordinator_agent_instractions import get_coordinator_agent_instructions
from inc.n8n_sub_agent import N8NSubAgent
from inc.share_data import SharedData


logger = logging.getLogger("multi-agent-system")


class CoordinatorAgent(Agent):
    """
    Coordinator agent that evaluates requests and routes them to specialized agents.
    """

    def __init__(self,  instructions: str, chat_ctx: Optional[ChatContext] = NOT_GIVEN,
    ) -> None:
        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        """Called when the agent is added to the session."""
        logger.info("Coordinator agent started")
        self.session.userdata.currentAgent = "coordinator"
        userdata: SharedData = self.session.userdata
        logger.info(f"chat context: {self.session._chat_ctx}")
        if(userdata.first_entry):
            userdata.first_entry = False
            self.session.generate_reply(
                instructions="Greet the user and ask how you can help them today."
            )
        else:
            self.session.generate_reply(
                instructions="Continue the conversation."
            )

    @function_tool
    async def route_to_agent(
        self,
        context: RunContext[SharedData],
        agent_id: str,
        query: str
    ):
        """
        Route a request to a specialized agent.

        Args:
            agent_id: ID of the agent
            query: The user's query to send to the agent
        """
        if(context.userdata.currentAgent!= "coordinator"):
            return ""
        # Store the query in shared data
        # context.userdata.user_query = query
        # context.userdata.agent_id = agent_id
        context.userdata.chat_context = self._chat_ctx
        agent_url = f"{N8N_BASE_URL}/webhook/{agent_id}/adi-sub-agent-trigger"
        # Create the specialized agent with the provided URL
        context.userdata.currentAgent = f"n8n_{agent_id}"
        initial_chat_ctx = ChatContext()
        n8n_agent = N8NSubAgent(
            api_url=agent_url,
            chat_ctx=initial_chat_ctx,
            sessionId=str(uuid.uuid4()),
            agent_id=agent_id,
            # context=context,
            query=query
        )

        return n8n_agent
