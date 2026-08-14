import os
from shared.logger import get_logger
from shared.config import DRY_RUN
from shared.memory import MemoryManager
from agents.social_agent.analytics_agent import AnalyticsAgent
from agents.social_agent.research_agent import ResearchAgent
from agents.social_agent.strategist_agent import StrategistAgent
from agents.social_agent.creator_agent import CreatorAgent
from agents.social_agent.publisher_agent import PublisherAgent
from agents.social_agent.critic_agent import CriticAgent
from agents.social_agent.community_agent import CommunityAgent
from agents.social_agent.monitor_agent import MonitorAgent
from agents.social_agent.news_agent import NewsAgent
from agents.social_agent.serious_agent import SeriousAgent

logger = get_logger("SocialAgentCoordinator")

class SocialAgentCoordinator:
    def __init__(self):
        self.analytics = AnalyticsAgent()
        self.researcher = ResearchAgent()
        self.strategist = StrategistAgent()
        self.creator = CreatorAgent()
        self.publisher = PublisherAgent()
        self.critic = CriticAgent()
        self.community = CommunityAgent()
        self.monitor = MonitorAgent()
        self.news_agent = NewsAgent()
        self.serious_agent = SeriousAgent()
        self.memory = MemoryManager()
        self.dry_run = DRY_RUN

    async def run(self, check_events: bool = False):
        logger.info("Starting Social Agent Pipeline...")
        
        # Step 0: Event Monitoring (Optional)
        breaking_event = None
        if check_events:
            event_status = self.monitor.check_for_breaking_news()
            if not event_status.get("is_breaking"):
                logger.info("No breaking news found. Exiting event-driven run early.")
                return
            breaking_event = event_status.get("event_summary")
        
        # Step 1: Analytics
        analytics_data = await self.analytics.fetch_and_save_performance()
        
        # Step 2: Research
        research_data = await self.researcher.fetch_daily_research()
        if breaking_event:
            research_data['macro_news'] = f"URGENT BREAKING NEWS: {breaking_event}\n" + research_data['macro_news']
        
        # Step 3: Strategy
        persona_profile = self.strategist.generate_persona(research_data, analytics_data)
        
        # Step 4: Creation & Critic Loop
        content = None
        feedback = None
        for attempt in range(3):
            content = self.creator.generate_unique_quote(persona_profile, critic_feedback=feedback)
            evaluation = self.critic.evaluate_content(content, persona_profile)
            if evaluation.get("pass"):
                break
            else:
                feedback = evaluation.get("feedback", "General failure. Try again.")
                logger.info(f"Critic rejected content. Retrying... (Attempt {attempt+1}/3)")
        
        quote = content.get("image_quote", "")
        x_post_text = content.get("x_post_text", quote)
        caption = content.get("meta_caption", "")
        
        # Step 5: Publishing (Render)
        image_path = await self.publisher.render_tweet_image(quote)
        
        print("\n" + "="*80)
        print("\033[1;96m" + " FINAL CONTENT GENERATED ".center(80, "=") + "\033[0m")
        print("="*80)
        print(f"\033[1;93m[IMAGE QUOTE (No Hashtags)]:\033[0m\n{quote}\n")
        print(f"\033[1;94m[X POST TEXT (Quote + Hashtags)]:\033[0m\n{x_post_text}\n")
        print(f"\033[1;92m[META CAPTION]:\033[0m\n{caption}\n")
        print(f"\033[1;95m[ASSET LOCATION]:\033[0m\n{image_path}")
        print("="*80 + "\n")
        
        x_success = True
        meta_success = True
        if self.dry_run:
            logger.info("DRY_RUN IS ON: Output validated. Network posting bypassed.")
        else:
            logger.info("DRY_RUN IS OFF: Executing network posts...")
            # For Persona Agent, post text only to X, and image to Meta
            x_success = await self.publisher.post_to_x_stealth(x_post_text)
            meta_success = self.publisher.post_to_meta(caption=caption, image_path=image_path)
            
        # Step 6: Community Engagement
        if not self.dry_run:
            await self.community.reply_to_mentions(persona_profile)
            
        # Step 7: Memory Log
        self.memory.save_post(quote, caption, persona_profile.get("emotional_filter", "None"))
        logger.info("Social Agent Pipeline Complete.")
        return {
            "image_path": image_path,
            "x_post_text": x_post_text,
            "meta_caption": caption,
            "x_success": x_success,
            "meta_success": meta_success
        }

    async def run_news(self):
        logger.info("Starting Social News Alert Pipeline...")
        
        # Step 1: Research
        research_data = await self.researcher.fetch_daily_research()
        
        # Step 2: Content Generation
        content = self.news_agent.generate_news_post(research_data)
        
        news_text = content.get("news_content", "")
        x_post_text = content.get("x_post_text", news_text)
        caption = content.get("meta_caption", "")
        
        # Step 3: Publishing (Render)
        image_path = await self.publisher.render_news_image(news_text)
        
        print("\n" + "="*80)
        print("\033[1;96m" + " FINAL NEWS CONTENT GENERATED ".center(80, "=") + "\033[0m")
        print("="*80)
        print(f"\033[1;93m[IMAGE NEWS]:\033[0m\n{news_text}\n")
        print(f"\033[1;94m[X POST TEXT]:\033[0m\n{x_post_text}\n")
        print(f"\033[1;92m[META CAPTION]:\033[0m\n{caption}\n")
        print(f"\033[1;95m[ASSET LOCATION]:\033[0m\n{image_path}")
        print("="*80 + "\n")
        
        x_success = True
        meta_success = True
        if self.dry_run:
            logger.info("DRY_RUN IS ON: Output validated. Network posting bypassed.")
        else:
            logger.info("DRY_RUN IS OFF: Executing network posts...")
            x_success = await self.publisher.post_to_x_stealth(x_post_text, image_path=image_path)
            meta_success = self.publisher.post_to_meta(caption=caption, image_path=image_path)
            
        logger.info("Social News Pipeline Complete.")
        return {
            "image_path": image_path,
            "x_post_text": x_post_text,
            "meta_caption": caption,
            "x_success": x_success,
            "meta_success": meta_success
        }

    async def run_serious(self):
        logger.info("Starting Serious Trading Advice Pipeline...")
        
        research_data = await self.researcher.fetch_daily_research()
        
        content = self.serious_agent.generate_serious_quote(research_data)
        quote = content.get("image_quote", "")
        # Enforce that X post text is identical to the image quote, plus any hashtags returned
        x_text_from_agent = content.get("x_post_text", "")
        hashtags = " ".join([word for word in x_text_from_agent.split() if word.startswith("#")])
        x_post_text = f"{quote} {hashtags}".strip()
        
        caption = content.get("meta_caption", "")
        
        image_path = await self.publisher.render_tweet_image(quote, filename="serious_quote.png")
        
        print("\n" + "="*80)
        print("\033[1;96m" + " FINAL SERIOUS CONTENT GENERATED ".center(80, "=") + "\033[0m")
        print("="*80)
        print(f"\033[1;93m[IMAGE QUOTE]:\033[0m\n{quote}\n")
        print(f"\033[1;94m[X POST TEXT]:\033[0m\n{x_post_text}\n")
        print(f"\033[1;92m[META CAPTION]:\033[0m\n{caption}\n")
        print(f"\033[1;95m[ASSET LOCATION]:\033[0m\n{image_path}")
        print("="*80 + "\n")
        
        x_success = True
        meta_success = True
        if self.dry_run:
            logger.info("DRY_RUN IS ON: Output validated. Network posting bypassed.")
        else:
            logger.info("DRY_RUN IS OFF: Executing network posts...")
            # For Serious Agent, post text only to X, and image to Meta
            x_success = await self.publisher.post_to_x_stealth(x_post_text)
            meta_success = self.publisher.post_to_meta(caption=caption, image_path=image_path)
            
        logger.info("Serious Advice Pipeline Complete.")
        return {
            "image_path": image_path,
            "x_post_text": x_post_text,
            "meta_caption": caption,
            "x_success": x_success,
            "meta_success": meta_success
        }

    async def run_manual(self):
        logger.info("Starting Manual Post Pipeline...")
        print("\n--- Manual Custom Post ---")
        print("1. Text Quote Only (renders standard quote image)")
        print("2. Photo + Caption (posts photo to X and Meta, uses image template for Meta)")
        post_type = input("Choose option (1-2): ").strip()
        
        if post_type == "1":
            quote = input("\nEnter the wording for the quote (this goes on the image and X): ").strip()
            if not quote:
                print("Quote cannot be empty. Aborting.")
                return
                
            caption = input("Enter the caption (for Instagram and Facebook): ").strip()
            
            image_path = await self.publisher.render_tweet_image(quote, filename="manual_quote.png")
            
            print("\n" + "="*80)
            print("\033[1;96m" + " FINAL MANUAL CONTENT GENERATED ".center(80, "=") + "\033[0m")
            print("="*80)
            print(f"\033[1;93m[IMAGE QUOTE & X POST]:\033[0m\n{quote}\n")
            print(f"\033[1;92m[META CAPTION]:\033[0m\n{caption}\n")
            print(f"\033[1;95m[ASSET LOCATION]:\033[0m\n{image_path}")
            print("="*80 + "\n")
            
            if self.dry_run:
                logger.info("DRY_RUN IS ON: Output validated. Network posting bypassed.")
            else:
                logger.info("DRY_RUN IS OFF: Executing network posts...")
                await self.publisher.post_to_x_stealth(quote)
                self.publisher.post_to_meta(caption=caption, image_path=image_path)
                
        elif post_type == "2":
            quote = input("\nEnter the text/caption for this post (goes on X and Meta): ").strip()
            photo_path = input("Enter the absolute file path to the photo (e.g. /home/user/chart.png): ").strip()
            
            if not os.path.exists(photo_path):
                print(f"Error: Could not find file at {photo_path}. Aborting.")
                return
            
            # Render the Meta-friendly template containing the image
            rendered_image_path = await self.publisher.render_tweet_with_custom_photo(
                quote_text=quote, 
                custom_photo_path=photo_path,
                filename="manual_photo_quote.png"
            )
            
            print("\n" + "="*80)
            print("\033[1;96m" + " FINAL MANUAL PHOTO POST GENERATED ".center(80, "=") + "\033[0m")
            print("="*80)
            print(f"\033[1;93m[CAPTION]:\033[0m\n{quote}\n")
            print(f"\033[1;94m[ORIGINAL PHOTO]:\033[0m\n{photo_path}\n")
            print(f"\033[1;95m[RENDERED META ASSET]:\033[0m\n{rendered_image_path}")
            print("="*80 + "\n")
            
            if self.dry_run:
                logger.info("DRY_RUN IS ON: Output validated. Network posting bypassed.")
            else:
                logger.info("DRY_RUN IS OFF: Executing network posts...")
                # Post the raw photo and text to X
                await self.publisher.post_to_x_stealth(quote, image_path=photo_path)
                # Post the rendered template with photo to Meta
                self.publisher.post_to_meta(caption=quote, image_path=rendered_image_path)
        else:
            print("Invalid choice. Aborting manual post.")
            return
            
        logger.info("Manual Post Pipeline Complete.")

