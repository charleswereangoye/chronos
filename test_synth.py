import asyncio
import pytest
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
import logging

logging.basicConfig(level=logging.INFO)

@pytest.mark.asyncio
async def test_synth():
    synthesizer = ProfileSynthesizer()
    res = await synthesizer.synthesize("Test job description for a software engineer.")
    assert isinstance(res, dict)
    assert res.get("name") is not None

if __name__ == "__main__":
    asyncio.run(test_synth())

