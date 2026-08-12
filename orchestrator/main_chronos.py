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
        print("\nWhat do you want to do for today?")
        print("1. Update people about red folder news")
        print("2. Post a serious trading advice (no moods)")
        print("3. Post a persona-based quote (with moods)")
        print("4. Check for breaking news (event-driven)")
        print("5. Run all standard pipelines (News, Serious, Persona)")
        
        choice = input("Enter choice (1-5): ").strip()
        
        if choice == "1":
            await social_coordinator.run_news()
        elif choice == "2":
            await social_coordinator.run_serious()
        elif choice == "3":
            await social_coordinator.run()
        elif choice == "4":
            await social_coordinator.run(check_events=True)
        elif choice == "5":
            await social_coordinator.run_news()
            await social_coordinator.run_serious()
            await social_coordinator.run()
        else:
            print("Invalid choice. Exiting.")
    except Exception as e:
        logger.error(f"Chronos workflow failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_chronos())
