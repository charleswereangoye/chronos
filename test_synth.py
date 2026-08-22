import asyncio
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    synthesizer = ProfileSynthesizer()
    res = await synthesizer.synthesize("Test job description for a software engineer.")
    print("Result:")
    print(res)

if __name__ == "__main__":
    asyncio.run(test())
