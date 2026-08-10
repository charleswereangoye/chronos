import asyncio
import traceback
from agents.social_agent.analytics_agent import AnalyticsAgent

async def run():
    agent = AnalyticsAgent()
    try:
        await agent.fetch_and_save_performance()
    except Exception as e:
        traceback.print_exc()

asyncio.run(run())
