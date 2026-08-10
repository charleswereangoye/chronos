from shared.logger import get_logger
from shared.config import DRY_RUN
from shared.memory import MemoryManager
from agents.social_agent.analytics_agent import AnalyticsAgent
from agents.social_agent.research_agent import ResearchAgent
from agents.social_agent.strategist_agent import StrategistAgent
from agents.social_agent.creator_agent import CreatorAgent
from agents.social_agent.publisher_agent import PublisherAgent

logger = get_logger("SocialAgentCoordinator")

class SocialAgentCoordinator:
    def __init__(self):
        self.analytics = AnalyticsAgent()
        self.researcher = ResearchAgent()
        self.strategist = StrategistAgent()
        self.creator = CreatorAgent()
        self.publisher = PublisherAgent()
        self.memory = MemoryManager()

    async def run(self):
        logger.info("Starting Social Agent Pipeline...")
        
        # Step 0: Analytics
        analytics_data = await self.analytics.fetch_and_save_performance()
        
        # Step 1: Research
        research_data = await self.researcher.fetch_daily_research()
        
        # Step 2: Strategy
        persona_profile = self.strategist.generate_persona(research_data, analytics_data)
        
        # Step 3: Creation
        content = self.creator.generate_unique_quote(persona_profile)
        quote = content.get("image_quote", "")
        x_post_text = content.get("x_post_text", quote)
        caption = content.get("meta_caption", "")
        
        # Step 4: Publishing (Render)
        image_path = await self.publisher.render_tweet_image(quote)
        
        print("\n" + "="*80)
        print("\033[1;96m" + " FINAL CONTENT GENERATED ".center(80, "=") + "\033[0m")
        print("="*80)
        print(f"\033[1;93m[IMAGE QUOTE (No Hashtags)]:\033[0m\n{quote}\n")
        print(f"\033[1;94m[X POST TEXT (Quote + Hashtags)]:\033[0m\n{x_post_text}\n")
        print(f"\033[1;92m[META CAPTION]:\033[0m\n{caption}\n")
        print(f"\033[1;95m[ASSET LOCATION]:\033[0m\n{image_path}")
        print("="*80 + "\n")
        
        if DRY_RUN:
            logger.info("DRY_RUN IS ON: Output validated. Network posting bypassed.")
        else:
            logger.info("DRY_RUN IS OFF: Executing network posts...")
            await self.publisher.post_to_x_stealth(x_post_text)
            self.publisher.post_to_meta(caption=caption, image_path=image_path)
            
        # Step 5: Memory Log
        self.memory.save_post(quote, caption)
        logger.info("Social Agent Pipeline Complete.")
