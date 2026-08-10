import asyncio
import sys
import os

# Ensure the root chronos directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.social_agent.social_coordinator import SocialAgentCoordinator
from shared.logger import get_logger

logger = get_logger("MainOrchestrator")

async def run_chronos():
    logger.info("Starting Chronos Master Orchestrator...")
    
    try:
        social_coordinator = SocialAgentCoordinator()
        await social_coordinator.run()
    except Exception as e:
        logger.error(f"Chronos workflow failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_chronos())
