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
        
        while True:
            print("\n=== Welcome to Chronos Master Orchestrator ===")
            print("Which agent do you want to use?")
            print("1. Social Agent")
            print("2. Job Seeking Agent")
            print("3. Forex Agent")
            print("4. Daily Updates Agent")
            print("0. Exit")
            
            agent_choice = input("Enter choice (0-4): ").strip()
            
            if agent_choice == "0":
                print("Exiting Chronos Master Orchestrator. Goodbye!")
                break
            elif agent_choice == "1":
                while True:
                    print("\n--- Social Agent Menu ---")
                    print("What do you want to do for today?")
                    print("1. Update people about red folder news")
                    print("2. Post a serious trading advice (no moods)")
                    print("3. Post a persona-based quote (with moods)")
                    print("4. Check for breaking news (event-driven)")
                    print("5. Run all standard pipelines (News, Serious, Persona)")
                    print("6. Create a custom manual post")
                    print("0. Back to Main Menu")
                    
                    choice = input("Enter choice (0-6): ").strip()
                    
                    if choice == "0":
                        break
                    elif choice == "1":
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
                    elif choice == "6":
                        await social_coordinator.run_manual()
                    else:
                        print("Invalid choice. Please try again.")
            elif agent_choice in ["2", "3", "4"]:
                print("\nThis agent is still in production.")
            else:
                print("Invalid choice. Please try again.")
    except (KeyboardInterrupt, EOFError):
        print("\nExiting via keyboard interrupt. Goodbye!")
    except Exception as e:
        logger.error(f"Chronos workflow failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_chronos())
