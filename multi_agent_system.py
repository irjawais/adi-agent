"""
Multi-Agent System using LiveKit Agent Framework.

This system implements a coordinator agent that routes requests to specialized agents.
"""
import logging
import uuid
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
import json
from inc.get_n8n_sub_agents import get_n8n_agents
from inc.share_data import SharedData
from livekit.plugins import deepgram, openai, silero
from livekit.agents.voice import MetricsCollectedEvent
from inc.coordinator_agent import CoordinatorAgent
from inc.coordinator_agent_instractions import get_coordinator_agent_instructions
from livekit.plugins.turn_detector.english import EnglishModel
# To reload environment variables from .env file
logger = logging.getLogger("multi-agent-system")


def prewarm(proc: JobProcess):
    """Preload models and resources when the worker starts."""
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    """Main entry point for the agent system."""
    logger.info("Connecting to the room...")
    await ctx.connect()
    particepent = await ctx.wait_for_participant()
    avaiable_agents = await get_n8n_agents()
    metaData = json.loads(particepent.metadata)
    insractions = get_coordinator_agent_instructions(avaiable_agents)
    userdata = SharedData(
        eventSessionId=metaData.get("eventSessionId", str(uuid.uuid4())),
        availableAgents=avaiable_agents,
    )
    # Create the agent session
    session = AgentSession[SharedData](
        vad=ctx.proc.userdata["vad"],
        turn_detection=EnglishModel(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),
        userdata=userdata,
    )

    # Set up metrics collection
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)
    initial_ctx = ChatContext()
    # initial_ctx.add_message(role="assistant", content=f"The user's name is {user_name}.")
    userdata.chat_context = initial_ctx
    userdata.coordinator_agent = CoordinatorAgent(instructions=insractions, chat_ctx=initial_ctx)

    # Start the session with the coordinator agent
    await session.start(
        agent=userdata.coordinator_agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )
    logger.info("Agent session started.")
    # session.generate_reply(
    #     instructions="Greet the user and ask how you can help them today."
    # )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
