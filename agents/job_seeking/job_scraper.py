import logging
import requests
import json
from typing import List, Dict, Any
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
from shared.llm import generate_content_with_failover

logger = logging.getLogger("JobScraper")

NON_TECH_TERMS = [
    "gardener", "driver", "nurse", "teacher", "chef", "cook", "scheduler",
    "estimator", "receptionist", "plumber", "technician", "sales rep",
    "account executive", "customer success", "warehouse", "cleaner", "barista",
    "consultant at self-employed", "electrician", "mechanic"
]

SOFTWARE_TERMS = [
    "software", "developer", "engineer", "frontend", "front-end", "backend",
    "back-end", "full stack", "fullstack", "full-stack", "web developer",
    "python", "react", "typescript", "javascript", "node", "next.js",
    "fastapi", "flask", "django", "programmer", "coding", "intern", "app developer",
    "data engineer", "ai engineer", "cloud infrastructure"
]

SENIOR_TERMS = [
    "senior", "sr.", "sr ", "principal", "staff", "lead", "director",
    "vp ", "head of", "architect", "manager", "7+ years", "8+ years", "10+ years"
]

class JobScraper:
    def __init__(self):
        self.synthesizer = ProfileSynthesizer()

    def is_early_career_friendly(self, job_title: str, description: str = "", tags: List[str] = None) -> bool:
        """Helper for backwards compatibility and unit testing."""
        return self.is_relevant_job(title=job_title, tags=tags or [], description=description, seniority_level="junior")

    def is_relevant_job(self, title: str, tags: List[str], description: str, seniority_level: str = "junior") -> bool:
        """Filters jobs based on domain relevance and the candidate's current seniority level."""
        title_lower = title.lower()
        tags_str = " ".join([str(t).lower() for t in tags])
        desc_lower = description.lower()

        # Hard exclude non-tech / irrelevant professions
        if any(term in title_lower for term in NON_TECH_TERMS):
            return False

        # Must have software/tech relevance in title, tags, or description
        is_software = (
            any(term in title_lower for term in SOFTWARE_TERMS)
            or any(term in tags_str for term in ["dev", "software", "programming", "python", "react", "typescript", "fullstack", "backend", "frontend"])
        )
        if not is_software:
            return False

        # Seniority check for early-career / junior candidates
        if seniority_level in ["intern", "junior", "entry-level", "student"]:
            if any(term in title_lower for term in SENIOR_TERMS):
                return False

        return True

    def fetch_remotive_jobs(self, seniority_level: str = "junior") -> List[Dict[str, Any]]:
        try:
            url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=40"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                jobs = resp.json().get("jobs", [])
                filtered = []
                for j in jobs:
                    title = j.get("title", "")
                    tags = j.get("tags", [])
                    desc = (j.get("description") or "")[:400]
                    if self.is_relevant_job(title, tags, desc, seniority_level):
                        filtered.append({
                            "source": "Remotive",
                            "title": title,
                            "company": j.get("company_name", "Unknown"),
                            "url": j.get("url", ""),
                            "tags": tags,
                            "description": desc
                        })
                return filtered[:12]
        except Exception as e:
            logger.warning(f"Failed to fetch Remotive jobs: {e}")
        return []

    def fetch_arbeitnow_jobs(self, seniority_level: str = "junior") -> List[Dict[str, Any]]:
        try:
            url = "https://www.arbeitnow.com/api/job-board-api"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                jobs = resp.json().get("data", [])
                filtered = []
                for j in jobs:
                    title = j.get("title", "")
                    tags = j.get("tags", [])
                    desc = (j.get("description") or "")[:400]
                    if self.is_relevant_job(title, tags, desc, seniority_level):
                        filtered.append({
                            "source": "Arbeitnow",
                            "title": title,
                            "company": j.get("company_name", "Unknown"),
                            "url": j.get("url", ""),
                            "tags": tags,
                            "description": desc
                        })
                return filtered[:12]
        except Exception as e:
            logger.warning(f"Failed to fetch Arbeitnow jobs: {e}")
        return []

    def fetch_remoteok_jobs(self, seniority_level: str = "junior") -> List[Dict[str, Any]]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get("https://remoteok.com/api", headers=headers, timeout=10)
            if resp.status_code == 200:
                raw_jobs = resp.json()
                filtered = []
                for j in raw_jobs:
                    if isinstance(j, dict) and j.get("position"):
                        title = j.get("position", "")
                        tags = j.get("tags", [])
                        desc = (j.get("description") or "")[:400]
                        if self.is_relevant_job(title, tags, desc, seniority_level):
                            filtered.append({
                                "source": "RemoteOK",
                                "title": title,
                                "company": j.get("company", "Unknown"),
                                "url": j.get("url", ""),
                                "tags": tags,
                                "description": desc
                            })
                return filtered[:12]
        except Exception as e:
            logger.warning(f"Failed to fetch RemoteOK jobs: {e}")
        return []

    def fetch_jobicy_jobs(self, seniority_level: str = "junior") -> List[Dict[str, Any]]:
        try:
            url = "https://jobicy.com/api/v2/remote-jobs?count=30&tag=software-engineering"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                jobs = resp.json().get("jobs", [])
                filtered = []
                for j in jobs:
                    title = j.get("jobTitle", "")
                    tags = j.get("jobType", [])
                    desc = (j.get("jobExcerpt") or "")[:400]
                    if self.is_relevant_job(title, tags, desc, seniority_level):
                        filtered.append({
                            "source": "Jobicy",
                            "title": title,
                            "company": j.get("companyName", "Unknown"),
                            "url": j.get("url", ""),
                            "tags": tags,
                            "description": desc
                        })
                return filtered[:10]
        except Exception as e:
            logger.warning(f"Failed to fetch Jobicy jobs: {e}")
        return []

    async def find_matches(self, force_refresh_profile: bool = False) -> str:
        logger.info("Retrieving live candidate profile for job radar matching...")
        candidate_data = await self.synthesizer.get_base_profile(force_refresh=force_refresh_profile)
        
        seniority = candidate_data.get("seniority_level", "junior")
        logger.info(f"Scanning remote job boards matching candidate level: '{seniority}'...")

        all_jobs = (
            self.fetch_remotive_jobs(seniority_level=seniority)
            + self.fetch_arbeitnow_jobs(seniority_level=seniority)
            + self.fetch_remoteok_jobs(seniority_level=seniority)
            + self.fetch_jobicy_jobs(seniority_level=seniority)
        )
        
        if not all_jobs:
            return "ℹ️ No remote openings matching your criteria found on the monitored boards right now. Check back shortly!"

        skills_list = candidate_data.get("skills", [])
        skills_str = ", ".join(skills_list) if isinstance(skills_list, list) else str(skills_list)
        projects_list = candidate_data.get("top_projects", [])
        projects_str = ", ".join(projects_list) if isinstance(projects_list, list) else str(projects_list)

        prompt = f"""
You are an expert technical career advisor matching an engineer's real-time qualifications to open remote positions.

CANDIDATE PROFILE (Live Verified Data):
- Name: {candidate_data.get('name')}
- Current Title & Status: {candidate_data.get('title')} ({candidate_data.get('current_status')})
- Seniority Level: {seniority}
- Core Skills: {skills_str}
- Key Projects & Experience: {projects_str}
- Location: {candidate_data.get('location')}

OPEN REMOTE JOB LISTINGS:
{json.dumps(all_jobs[:25], indent=2)}

TASK:
1. Select the TOP 3 to 5 jobs where this candidate has the strongest competitive advantage based strictly on their actual stack ({skills_str}) and current level ({seniority}).
2. Rank them by Match Quality.
3. ABSOLUTELY NO em-dashes (—). Use standard hyphens (-) or colons (:).
4. For each selected match, format with clean markdown:
   🎯 **[Job Title]** at **[Company]**
   📊 **Match Score & Level**: (e.g. 92% Match - Junior / Full-Stack)
   💡 **Why You Fit**: 1-2 punchy sentences explicitly detailing how their skills ({skills_str}) directly solve the role's requirements.
   🔗 **Direct Apply URL**: [Link]
"""
        response = generate_content_with_failover(prompt_text=prompt)
        return response.text.strip()
