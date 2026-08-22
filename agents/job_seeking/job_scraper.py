import logging
import requests
import json
from google import genai
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
import os
from shared.config import get_gemini_client_and_model

logger = logging.getLogger(__name__)

class JobScraper:
    def __init__(self):
        self.client, self.model_name = get_gemini_client_and_model()
        self.synthesizer = ProfileSynthesizer()

    async def find_matches(self) -> str:
        logger.info("Synthesizing candidate data for job matching...")
        candidate_data = await self.synthesizer.synthesize()
        skills_str = ", ".join(candidate_data.get("skills", []))
        
        logger.info("Fetching remote jobs from Remotive API...")
        try:
            # Fetch Software Dev jobs
            response = requests.get("https://remotive.com/api/remote-jobs?category=software-dev&limit=50")
            response.raise_for_status()
            jobs = response.json().get("jobs", [])
            
            # Simplify job data to save tokens
            simplified_jobs = []
            for j in jobs[:20]: # Take top 20 recent
                simplified_jobs.append({
                    "title": j.get("title"),
                    "company": j.get("company_name"),
                    "url": j.get("url"),
                    "description": j.get("description", "")[:200] + "..." # Snippet only
                })
        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}")
            return "Failed to fetch jobs from API."
            
        prompt = f"""
You are an expert technical recruiter matching candidates to open jobs.
Here is the candidate's profile summary and skills:
{json.dumps(candidate_data)}

Here is a list of recent remote job postings:
{json.dumps(simplified_jobs)}

Select the Top 3 to 5 jobs that BEST match the candidate's skills and experience. 
For each matched job, provide:
1. Job Title at Company Name
2. A 1-sentence reason why it's a good match based on their specific skills.
3. The URL to apply.

Format this nicely with Markdown.
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        
        return response.text.strip()
