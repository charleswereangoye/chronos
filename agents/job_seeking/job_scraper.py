import logging
import requests
import json
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
from shared.llm import generate_content_with_failover

logger = logging.getLogger("JobScraper")

class JobScraper:
    def __init__(self):
        self.synthesizer = ProfileSynthesizer()

    def is_early_career_friendly(self, job_title: str, description: str) -> bool:
        """Filters out senior/executive roles and prioritizes junior/intern/early-career friendly posts."""
        title_lower = job_title.lower()
        desc_lower = description.lower()
        
        # Hard exclusions
        excluded_keywords = [
            "senior", "sr.", "sr ", "lead", "principal", "staff", 
            "director", "vp ", "head of", "architect", "manager",
            "7+ years", "8+ years", "10+ years", "5+ years"
        ]
        if any(kw in title_lower for kw in excluded_keywords):
            return False
            
        # Positive indicators
        junior_keywords = [
            "junior", "jr", "intern", "internship", "graduate", 
            "entry", "associate", "trainee", "early career", "level 1", "level i"
        ]
        has_junior_keyword = any(kw in title_lower or kw in desc_lower for kw in junior_keywords)
        
        # If it doesn't say "senior" and is a general software dev role, we also allow it
        return True

    def fetch_remotive_jobs(self) -> list:
        try:
            url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=40"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                jobs = resp.json().get("jobs", [])
                filtered = []
                for j in jobs:
                    title = j.get("title", "")
                    desc = (j.get("description") or "")[:400]
                    if self.is_early_career_friendly(title, desc):
                        filtered.append({
                            "title": title,
                            "company": j.get("company_name"),
                            "url": j.get("url"),
                            "tags": j.get("tags", []),
                            "description": desc
                        })
                return filtered[:15]
        except Exception as e:
            logger.warning(f"Failed to fetch Remotive jobs: {e}")
        return []

    def fetch_arbeitnow_jobs(self) -> list:
        try:
            url = "https://www.arbeitnow.com/api/job-board-api"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                jobs = resp.json().get("data", [])
                filtered = []
                for j in jobs:
                    title = j.get("title", "")
                    desc = (j.get("description") or "")[:400]
                    if self.is_early_career_friendly(title, desc):
                        filtered.append({
                            "title": title,
                            "company": j.get("company_name"),
                            "url": j.get("url"),
                            "tags": j.get("tags", []),
                            "description": desc
                        })
                return filtered[:15]
        except Exception as e:
            logger.warning(f"Failed to fetch Arbeitnow jobs: {e}")
        return []

    async def find_matches(self) -> str:
        logger.info("Retrieving student/junior profile for job radar matching...")
        candidate_data = await self.synthesizer.get_base_profile()
        
        logger.info("Scanning remote job boards for Junior / Intern / Early-Career opportunities...")
        all_jobs = self.fetch_remotive_jobs() + self.fetch_arbeitnow_jobs()
        
        if not all_jobs:
            return "ℹ️ No early-career / junior remote openings found on the monitored boards right now. Check back during normal posting hours!"

        prompt = f"""
You are an expert career agent and technical recruiter helping a talented Software Engineering Student / Junior Full-Stack Developer find the best matching entry-level, internship, or junior remote tech jobs.

CANDIDATE BACKGROUND:
Name: {candidate_data.get('name')}
Status: Software Engineering Student & Full-Stack Developer
Core Skills: {candidate_data.get('skills')}
Key Projects: Next.js/React full-stack apps, Python/Flask backend APIs, PostgreSQL, Docker containerization, Autonomous AI Agent workflows.

OPEN REMOTE JOB LISTINGS (Pre-filtered for Early-Career):
{json.dumps(all_jobs[:25], indent=2)}

TASK:
1. Identify the TOP 3 to 5 jobs where this candidate has the highest chance of winning an interview based on their real stack (JavaScript/TypeScript, React, Python, APIs, SQL, Docker).
2. Rank them by Match Quality.
3. For each match, provide:
   - **Job Title & Company**: [Title] at [Company]
   - **Match Score & Seniority**: (e.g. 92% Match - Junior / Entry-Level Friendly)
   - **Why You Fit**: 1-2 concise, punchy sentences connecting their actual skills (React/Python/Docker/APIs) to the role's requirements.
   - **Direct Apply URL**: [Link]

FORMAT WITH CLEAN MARKDOWN:
"""
        response = generate_content_with_failover(prompt_text=prompt)
        return response.text.strip()
