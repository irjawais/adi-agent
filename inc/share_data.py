from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union, Tuple
from livekit.agents import ChatContext

@dataclass
class SharedData:
    """Shared data between agents."""
    currentAgent: Optional[str] = None
    sessionId: Optional[Dict[str, Any]] = None
    agentId: Optional[str] = None
    availableAgents: List[Dict[str, Any]] = None
    sessionId: Optional[str] = None
    eventSessionId: Optional[str] = None
    first_entry: bool = True
    coordinator_agent_instructionsq: Optional[str] = None
    chat_context: Optional[ChatContext] = None
    coordinator_agent: Optional[any] = None
