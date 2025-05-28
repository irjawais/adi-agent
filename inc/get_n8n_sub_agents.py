import logging
from inc.config import N8N_API_KEY, N8N_API_URL
import aiohttp
from typing import Dict, Any, List

logger = logging.getLogger("multi-agent-system")


async def get_n8n_agents() -> List[Dict[str, Any]]:
    """
    Get a list of available agents from n8n workflows.

    This function:
    1. Connects to the n8n API
    2. Gets all active workflows
    3. Filters workflows that have first node type "CUSTOM.adiSubAgent"
    4. Extracts agent parameters (agentName and agentRole) from each workflow

    Returns:
        A list of available agents with their name and role.
    """
    try:
        # Prepare headers for n8n API
        headers = {"X-N8N-API-KEY": N8N_API_KEY} if N8N_API_KEY else {}

        # Get all active workflows from n8n
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{N8N_API_URL}/workflows",
                headers=headers,
                timeout=30
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"n8n API error: {response.status} - {error_text}")
                    return []

                workflows = await response.json()
                
        workflows = workflows.get("data", [])
        # Filter workflows with first node type "CUSTOM.adiSubAgent"
        available_agents = ""

        for workflow in workflows:
            # Skip inactive workflows
            if not workflow.get("active", False):
                continue

            # Get nodes from the workflow
            nodes = workflow.get("nodes", [])

            # Find the first node
            first_node = None
            for node in nodes:
                # Look for the node with type "CUSTOM.adiSubAgent"
                if node.get("type") == "CUSTOM.adiSubAgent":
                    first_node = node
                    break

            # Skip if no matching node found
            if not first_node:
                continue

            # Extract agent parameters
            parameters = first_node.get("parameters", {})
            agent_name = parameters.get("agentName", "Unknown Agent")
            agent_role = parameters.get("agentRole", "No role specified")
            agent_id = first_node.get("webhookId", "No webhook ID specified")

            # Add to available agents list
            available_agents += f"\n==== Agent ID: {agent_id}====\n"
            available_agents += f"Agent Name: {agent_name}\n"
            available_agents += f"Agent Role: {agent_role}\n\n"
            

        logger.info(f"Found {len(available_agents)} available agents from n8n workflows")
        logger.info(f"Available agents: {available_agents}")
        return available_agents

    except Exception as e:
        logger.error(f"Error getting available agents from n8n: {e}")
        raise e
        return []

