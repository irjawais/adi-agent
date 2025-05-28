# Multi-Agent System with LiveKit Agent Framework

This project implements a multi-agent architecture using the LiveKit Agent Framework:

1. **Coordinator Agent**
   - Acts as a router/dispatcher
   - Evaluates incoming requests
   - Gets available agents from n8n workflows or an agent registry API
   - Decides which specialized agent should handle each request
   - Routes requests to the appropriate agent with its URL
   - Manages the flow of information between agents

2. **Specialized Agent**
   - Acts as a proxy to an external API endpoint
   - Uses a custom LLM class implementation that connects to the external API
   - Processes user requests through the external API
   - Detects when tasks are completed and returns control to the coordinator

## Setup

1. Install dependencies:
```bash
pip install "livekit-agents[openai,silero,deepgram]~=1.0" python-dotenv
```

2. Set up environment variables in a `.env` file:
```
LIVEKIT_URL="wss://YOUR_PROJECT_URL.livekit.cloud"
LIVEKIT_API_KEY="YOUR_LK_API_KEY"
LIVEKIT_API_SECRET="YOUR_LK_API_SECRET"

OPENAI_API_KEY="sk-..."
DEEPGRAM_API_KEY="..."

# Agent Registry API configuration
AGENT_REGISTRY_URL="https://api.example.com/agents"
AGENT_API_KEY="your-agent-registry-api-key"

# Specialized Agent API configuration
SPECIALIZED_AGENT_URL="https://api.example.com/agent"
SPECIALIZED_AGENT_KEY="your-specialized-agent-api-key"

# n8n API configuration
N8N_API_URL="http://localhost:5678/api/v1"
N8N_API_KEY="your-n8n-api-key"
```

## Running the Agent

1. Run in console mode (for testing):
```bash
python multi_agent_system.py console
```

2. Run in development mode (with hot reloading):
```bash
python multi_agent_system.py dev
```

3. Run in production mode:
```bash
python multi_agent_system.py start
```

## Architecture

The system uses the LiveKit Agent Framework to create a multi-agent architecture:

- `AgentSession`: Manages the overall session and coordinates between agents
- `CoordinatorAgent`: Evaluates requests, gets available agents from n8n workflows or a registry, and routes requests to appropriate specialized agents
- `SpecializedAgent`: Acts as a proxy to external API endpoints, using a custom LLM to process requests
- `CustomLLM`: Implements the LLM interface from livekit-agents to connect to external APIs, handling text generation without function calls or streaming

## n8n Integration

The system can integrate with n8n to discover and use agents:

1. **Agent Discovery**: The system automatically discovers agents from n8n workflows
2. **Filtering**: It filters workflows that have a first node of type "CUSTOM.adiSubAgent"
3. **Agent Parameters**: Each agent requires two parameters in the n8n workflow:
   - `agentName`: The name of the agent (e.g., "Adi")
   - `agentRole`: A description of the agent's role (e.g., "Greeting agent for Adi")
4. **Workflow Execution**: When a request is routed to an agent, the corresponding n8n workflow is executed
5. **Request Format**: The system sends requests to n8n workflows in the following format:
   ```json
   {
     "sessionId": "03049d5dbff945be9092d969f7918a31",
     "action": "sendMessage",
     "chatInput": "User's message here",
     "eventChannelId": "channel-123"
   }
   ```
   - The `sessionId` is obtained from the room metadata or generated if not available
   - The `action` is always "sendMessage"
   - The `chatInput` contains the user's message
   - The `eventChannelId` is obtained from the room metadata (included only if available)

6. **Response Format**: The n8n workflow should return a response in the following format:
   ```json
   {
     "output": "The agent's response text here. STATUS_OF_TASK=COMPLETED"
   }
   ```
   - The `STATUS_OF_TASK=COMPLETED` marker at the end of the response indicates that the task is complete
   - When this marker is detected, the system will automatically call the `task_completed` tool
   - The marker is removed from the final response shown to the user

## Testing

You can test the agent using:
1. The [LiveKit Agents Playground](https://agents-playground.livekit.io/)
2. Any LiveKit client SDK
3. Console mode for local testing
# ADI Agent
