import asyncio
from agents.social_agent.scout_agent import ScoutAgent

def main():
    scout = ScoutAgent()
    scout.download_youtube_meme("green screen meme template", "general")
    scout.download_youtube_meme("trading meme template", "general")

if __name__ == "__main__":
    main()
