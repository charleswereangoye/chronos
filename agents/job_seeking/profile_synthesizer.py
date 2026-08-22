import logging
import json
from agents.job_seeking.github_fetcher import GithubFetcher
from agents.job_seeking.linkedin_scraper import LinkedinScraper
from agents.job_seeking.resume_parser import ResumeParser
from google import genai
import os
from shared.config import get_gemini_client_and_model

logger = logging.getLogger(__name__)

class ProfileSynthesizer:
    def __init__(self):
        self.github = GithubFetcher()
        self.linkedin = LinkedinScraper()
        self.resume = ResumeParser()
        
        # Initialize Gemini Client using shared config
        self.client, self.model_name = get_gemini_client_and_model()

    async def synthesize(self, job_description: str = None) -> dict:
        """Gathers data from all sources and synthesizes a master candidate profile using Gemini. 
        If a job_description is provided, it tailors the profile to that specific job."""
        logger.info("Gathering raw candidate data...")
        
        resume_text = self.resume.extract_text()
        github_data = self.github.fetch_user_data()
        linkedin_data = await self.linkedin.scrape_profile()
        
        prompt = f"""
You are an expert technical recruiter and resume writer. I am going to give you raw data extracted from a candidate's Resume, their GitHub profile, and their LinkedIn profile.
Your task is to merge, clean, and synthesize this information into a single, cohesive JSON object representing their professional profile.

CRITICAL INSTRUCTIONS TO AVOID "AI" TONE:
1. ABSOLUTELY NO em-dashes (—). Use commas, colons, or parentheses instead if necessary.
2. Write bullet points and summaries like a real human engineer: direct action verbs, clear impact, absolutely no fluff.
3. Avoid overly flowery language, buzzword stuffing, or robotic phrasing (e.g., "proven track record", "highly motivated"). Keep it grounded and professional.
"""
        if job_description:
            prompt += f"""
CRITICAL INSTRUCTION: You have also been provided with a target Job Description below. 
You MUST heavily tailor the candidate's JSON profile to this job. 
- Rewrite the `summary` to directly address the core needs of this role.
- Prioritize and re-order the `skills` list to highlight technologies requested in the job description.
- Tweak the `experience` descriptions to emphasize overlapping achievements.

--- TARGET JOB DESCRIPTION ---
{job_description}
"""
        
        prompt += f"""
Here is the expected JSON schema (do not output anything other than raw valid JSON):
{{
    "name": "Full Name",
    "title": "Professional Title (e.g., Software Engineer)",
    "email": "Email Address",
    "phone": "Phone Number",
    "location": "City, Country",
    "target_company": "The name of the company from the target job description (if provided, otherwise leave empty). Clean and capitalize appropriately (e.g., 'Glovo', 'Google').",
    "summary": "A powerful 2-3 sentence professional summary highlighting their strongest skills and background based on all sources.",
    "experience": [
        {{
            "role": "Job Title",
            "company": "Company Name",
            "duration": "Start - End Date",
            "description": "1-2 sentences describing their impact."
        }}
    ],
    "skills": ["Skill1", "Skill2", "Skill3", "... (Top 8-10 skills total across resume and GitHub)"],
    "education": [
        {{
            "degree": "Degree Name",
            "institution": "School Name",
            "year": "Graduation Year"
        }}
    ]
}}

Raw Data:
--- RESUME ---
{resume_text}

--- GITHUB (Top Projects and Languages) ---
{json.dumps(github_data, indent=2)}

--- LINKEDIN ---
{json.dumps(linkedin_data, indent=2)}

Synthesize the above data and return ONLY the JSON object.
"""

        try:
            logger.info("Sending data to Gemini for synthesis...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            raw_json = response.text.strip()
            # Remove markdown code block if present
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:-3].strip()
            elif raw_json.startswith("```"):
                raw_json = raw_json[3:-3].strip()
                
            candidate_data = json.loads(raw_json)
            return candidate_data
            
        except Exception as e:
            logger.error(f"Failed to synthesize profile with Gemini: {e}")
            # Fallback to dummy data
            return {
                "name": "Error Generating Profile",
                "email": "error@example.com",
                "phone": "",
                "location": "",
                "summary": "Failed to synthesize data.",
                "experience": [],
                "skills": [],
                "education": []
            }
