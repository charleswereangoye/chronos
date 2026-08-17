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
from agents.social_agent.content_router import ContentRouter
from agents.social_agent.video_meme_agent import VideoMemeAgent
from agents.social_agent.scout_agent import ScoutAgent

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
        self.router = ContentRouter()
        self.video_agent = VideoMemeAgent()
        self.scout_agent = ScoutAgent()
        self.memory = MemoryManager()
        self.dry_run = DRY_RUN

    async def generate_persona_draft(self, check_events: bool = False):
        logger.info("Starting Social Agent Pipeline - Draft Generation...")
        
        breaking_event = None
        if check_events:
            event_status = self.monitor.check_for_breaking_news()
            if not event_status.get("is_breaking"):
                logger.info("No breaking news found. Exiting event-driven run early.")
                return None
            breaking_event = event_status.get("event_summary")
        
        analytics_data = await self.analytics.fetch_and_save_performance()
        research_data = await self.researcher.fetch_daily_research()
        if breaking_event:
            research_data['macro_news'] = f"URGENT BREAKING NEWS: {breaking_event}\n" + research_data['macro_news']
        
        persona_profile = self.strategist.generate_persona(research_data, analytics_data)
        
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
        
        return {
            "type": "persona",
            "quote": quote,
            "x_post_text": x_post_text,
            "caption": caption,
            "persona_profile": persona_profile
        }

    async def generate_news_draft(self):
        logger.info("Starting Social News Alert Pipeline - Draft Generation...")
        research_data = await self.researcher.fetch_daily_research()
        content = self.news_agent.generate_news_post(research_data)
        
        news_text = content.get("news_content", "")
        x_post_text = content.get("x_post_text", news_text)
        caption = content.get("meta_caption", "")
        
        return {
            "type": "news",
            "news_text": news_text,
            "x_post_text": x_post_text,
            "caption": caption
        }

    async def generate_serious_draft(self):
        logger.info("Starting Serious Trading Advice Pipeline - Draft Generation...")
        research_data = await self.researcher.fetch_daily_research()
        content = self.serious_agent.generate_serious_quote(research_data)
        
        quote = content.get("image_quote", "")
        x_text_from_agent = content.get("x_post_text", "")
        hashtags = " ".join([word for word in x_text_from_agent.split() if word.startswith("#")])
        x_post_text = f"{quote} {hashtags}".strip()
        caption = content.get("meta_caption", "")
        
        return {
            "type": "serious",
            "quote": quote,
            "x_post_text": x_post_text,
            "caption": caption
        }

    async def generate_video_draft(self):
        logger.info("Starting Video Reel Meme Pipeline - Draft Generation...")
        analytics_data = await self.analytics.fetch_and_save_performance()
        research_data = await self.researcher.fetch_daily_research()
        persona_profile = self.strategist.generate_persona(research_data, analytics_data)
        
        emotion = persona_profile.get("emotional_filter", "general")
        content = self.video_agent.generate_meme_content(emotion)
        template_video = self.video_agent.select_template(emotion)
        
        return {
            "type": "video",
            "overlay_text": content.get("overlay_text", ""),
            "caption": content.get("caption", ""),
            "hashtags": content.get("hashtags", ""),
            "emotion": emotion,
            "template_video": template_video
        }

    async def publish_approved_post(self, draft: dict):
        logger.info(f"Publishing approved post of type: {draft['type']}")
        
        image_path = None
        video_path = None
        x_post_text = draft.get('x_post_text', '')
        caption = draft.get('caption', '')
        quote = draft.get('quote') or draft.get('news_text') or draft.get('overlay_text')

        if draft['type'] == 'persona':
            image_path = await self.publisher.render_tweet_image(quote)
        elif draft['type'] == 'news':
            image_path = await self.publisher.render_news_image(quote)
        elif draft['type'] == 'serious':
            image_path = await self.publisher.render_tweet_image(quote, filename="serious_quote.png")
        elif draft['type'] == 'video':
            x_post_text = f"{quote}\n\n{draft['hashtags']}"
            caption = f"{caption}\n\n{draft['hashtags']}"
            
            # Render the static tweet image to use as the meme header!
            header_image_path = await self.publisher.render_tweet_image(quote, filename="video_header.png")
            
            template_video_path = draft.get('template_video')
            if not template_video_path:
                template_video_path = self.video_agent.select_template(draft['emotion'])
                
            video_path = self.video_agent.render_video(header_image_path, template_video_path)
            
        print("\n" + "="*80)
        print("\033[1;96m" + " FINAL CONTENT GENERATED ".center(80, "=") + "\033[0m")
        print("="*80)
        print(f"\033[1;93m[IMAGE/VIDEO TEXT]:\033[0m\n{quote}\n")
        print(f"\033[1;94m[X POST TEXT]:\033[0m\n{x_post_text}\n")
        print(f"\033[1;92m[META CAPTION]:\033[0m\n{caption}\n")
        print(f"\033[1;95m[ASSET LOCATION]:\033[0m\n{image_path or video_path}")
        print("="*80 + "\n")
        
        x_success = True
        meta_success = True
        if self.dry_run:
            logger.info("DRY_RUN IS ON: Output validated. Network posting bypassed.")
        elif draft['type'] == 'video':
            logger.info("DRY_RUN IS OFF: Executing network posts for video...")
            if video_path:
                x_success = await self.publisher.post_video_to_x(x_post_text, video_path)
                meta_success = self.publisher.post_reel_to_meta(caption, video_path)
                await self.publisher.post_to_tiktok_stealth(caption, video_path)
                self.memory.save_video_post(quote, caption, draft['emotion'], os.path.basename(video_path))
            else:
                logger.error("Skipping video network posts because video_path is empty (rendering failed).")
                x_success = False
                meta_success = False
        else:
            logger.info("DRY_RUN IS OFF: Executing network posts for static graphic...")
            x_success = await self.publisher.post_to_x_stealth(x_post_text, image_path=image_path if draft['type'] == 'news' else None)
            
            if image_path:
                meta_success = self.publisher.post_to_meta(caption=caption, image_path=image_path)
            else:
                meta_success = False
            
            if draft['type'] == 'persona':
                await self.community.reply_to_mentions(draft['persona_profile'])
                self.memory.save_post(quote, caption, draft['persona_profile'].get("emotional_filter", "None"))
                
        logger.info(f"{draft['type'].capitalize()} Pipeline Complete.")
        return {
            "image_path": image_path or video_path,
            "x_post_text": x_post_text,
            "meta_caption": caption
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
            
            rendered_image_path = await self.publisher.render_tweet_with_custom_photo(
                quote_text=quote, 
                custom_photo_path=photo_path,
                filename="manual_photo_quote.png"
            )
            
            if self.dry_run:
                logger.info("DRY_RUN IS ON: Output validated. Network posting bypassed.")
            else:
                logger.info("DRY_RUN IS OFF: Executing network posts...")
                await self.publisher.post_to_x_stealth(quote, image_path=photo_path)
                self.publisher.post_to_meta(caption=quote, image_path=rendered_image_path)
        else:
            print("Invalid choice. Aborting manual post.")
            return
            
        logger.info("Manual Post Pipeline Complete.")
