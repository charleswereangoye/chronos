import os
import json
import logging
from typing import Optional, Dict, Any

from agents.job_seeking.github_fetcher import GithubFetcher
from agents.job_seeking.linkedin_scraper import LinkedinScraper
from agents.job_seeking.resume_parser import ResumeParser
from shared.llm import generate_json_with_failover

logger = logging.getLogger("ProfileSynthesizer")

class ProfileSynthesizer:
    def __init__(self):
        self.github = GithubFetcher()
        self.linkedin = LinkedinScraper()
        self.resume = ResumeParser()
        self.state_dir = os.path.join(os.path.dirname(__file__), "state")
        self.cache_file = os.path.join(self.state_dir, "base_profile_cache.json")
        os.makedirs(self.state_dir, exist_ok=True)

    def _load_cached_profile(self) -> Optional[Dict[str, Any]]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data.get("name") and data.get("skills"):
                        logger.info("Loaded base candidate profile from cache.")
                        return data
            except Exception as e:
                logger.warning(f"Failed to read cache file: {e}")
        return None

    def _save_cached_profile(self, profile_data: Dict[str, Any]):
        try:
            temp_file = os.path.join(self.state_dir, f".tmp_cache_{os.getpid()}.json")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=4)
            os.replace(temp_file, self.cache_file)
            logger.info("Saved base candidate profile to cache.")
        except Exception as e:
            logger.error(f"Failed to save profile cache: {e}")

    async def get_base_profile(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Gets or builds the master base profile from Resume, GitHub, and LinkedIn."""
        if not force_refresh:
            cached = self._load_cached_profile()
            if cached:
                return cached

        logger.info("Gathering candidate data from Resume, GitHub, and LinkedIn...")
        resume_text = self.resume.extract_text()
        github_data = self.github.fetch_user_data()
        linkedin_data = await self.linkedin.scrape_profile()

        prompt = f"""
You are an expert technical recruiter specializing in placing top-tier Software Engineering Students, Interns, and Junior Full-Stack Developers into global remote roles.

ANALYZE THIS CANDIDATE DATA CAREFULLY:
The candidate is Charles Were Angoye, an ambitious Software Engineering student & Full-Stack Developer with hands-on internship experience (Infinity Innova) and strong GitHub projects.

CRITICAL INSTRUCTIONS:
1. ACCURATELY POSITION SENIORITY LEVEL:
   - The candidate is a Student / Junior Full-Stack Engineer / Intern.
   - DO NOT fabricate 10 years of senior corporate experience.
   - Instead, highlight their exceptional real-world skills: building full-stack applications (Next.js, React, Python, Flask, Node.js, PostgreSQL, Docker), autonomous agent pipelines, and practical internship achievements.
2. ABSOLUTELY NO em-dashes (—).
3. Formulate 2-3 high-impact bullet points for experience and project highlights using:
   [Strong Action Verb] + [Core Technical Problem / System] + [Impact / Tech Stack].
4. Extract verified contact details, skills, education, and internship history.

Expected JSON Schema:
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
            "role": "Backend Developer Intern",
            "company": "Infinity Innova",
            "duration": "Internship",
            "highlights": [
                "Developed RESTful backend endpoints and optimized database queries using Python and SQL.",
                "Integrated asynchronous API workflows and managed containerized testing environments with Docker."
            ]
        }},
        {{
            "role": "Full-Stack Project Lead",
            "company": "Chronos Multi-Agent Platform & Open Source",
            "duration": "2025 - Present",
            "highlights": [
                "Architected autonomous multi-agent orchestration pipelines using Python, Podman, and Playwright for real-time automation.",
                "Built responsive full-stack web applications using Next.js, React, Tailwind CSS, and PostgreSQL."
            ]
        }}
    ],
    "skills": ["JavaScript (ES6+)", "TypeScript", "Python (Flask / FastAPI)", "React / Next.js", "Tailwind CSS", "Node.js", "PostgreSQL / Supabase", "Docker / Podman", "REST APIs", "Linux (Arch/Bash)"],
    "education": [
        {{
            "degree": "B.S. in Software Engineering (In Progress)",
            "institution": "Software Engineering Institute",
            "year": "Expected 2026"
        }}
    ]
}}

Raw Data:
--- RESUME ---
{resume_text}

--- GITHUB ---
{json.dumps(github_data, indent=2)}

--- LINKEDIN ---
{json.dumps(linkedin_data, indent=2)}
"""
        fallback_profile = {
            "name": "Charles Were Angoye",
            "email": "charleswereangoye@gmail.com",
            "phone": "+254719403678 / +250795589824",
            "location": "Kigali, Rwanda / Nairobi, Kenya (GMT+2 / EAT)",
            "summary": "Software Engineering student and Full-Stack Developer specializing in modern React/Next.js frontends, Python/Flask backends, PostgreSQL, and containerized Docker environments. Seeking a remote global internship or junior software engineer role.",
            "experience": [
                {
                    "role": "Backend Developer Intern",
                    "company": "Infinity Innova",
                    "duration": "Internship",
                    "highlights": [
                        "Engineered RESTful API services and structured PostgreSQL database schemas for high-performance data processing.",
                        "Collaborated in Agile sprints, containerizing development environments with Docker for seamless team onboarding."
                    ]
                },
                {
                    "role": "Full-Stack & Autonomous Systems Developer",
                    "company": "Chronos Open Source & Projects",
                    "duration": "2025 - Present",
                    "highlights": [
                        "Architected containerized autonomous multi-agent systems using Python, Podman, and Playwright.",
                        "Developed dynamic responsive interfaces with Next.js, React, Tailwind CSS, and Supabase."
                    ]
                }
            ],
            "skills": ["JavaScript (ES6+)", "TypeScript", "Python (Flask / FastAPI)", "React / Next.js", "Tailwind CSS", "Node.js", "PostgreSQL / Supabase", "Docker / Podman", "REST APIs", "Linux (Arch/Bash)"],
            "education": [
                {
                    "degree": "B.S. in Software Engineering (In Progress)",
                    "institution": "University / Institute",
                    "year": "Expected 2026"
                }
            ]
        }

        try:
            profile = generate_json_with_failover(
                prompt_text=prompt,
                max_attempts=3,
                default_fallback=fallback_profile
            )
            self._save_cached_profile(profile)
            return profile
        except Exception as e:
            logger.error(f"Failed to synthesize student profile: {e}")
            return fallback_profile

    async def synthesize(self, job_description: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        """Synthesizes candidate profile, tailoring it specifically to a junior/internship job description."""
        base_profile = await self.get_base_profile(force_refresh=force_refresh)
        
        if not job_description or not job_description.strip():
            return base_profile

        logger.info("Tailoring student/junior profile to target job description...")
        tailor_prompt = f"""
You are an expert technical resume strategist for junior software engineers and students.
Tailor the candidate's JSON profile to align directly with the target job requirements below.

CRITICAL INSTRUCTIONS:
1. KEEP THE PROFILE HONEST AND ACCURATE: The candidate is an exceptional student / junior full-stack engineer. Do not claim 10 years of experience. Highlight their fast learning ability, hands-on internship, and concrete projects.
2. ABSOLUTELY NO em-dashes (—).
3. Align the `summary`, `skills`, and `highlights` to the tech stack mentioned in the job description (e.g. React, Next.js, Python, APIs, SQL, Docker).
4. Return ONLY valid JSON matching the schema.

--- TARGET JOB DESCRIPTION ---
{job_description[:4000]}

--- BASE CANDIDATE PROFILE ---
{json.dumps(base_profile, indent=2)}
"""
        try:
            tailored_profile = generate_json_with_failover(
                prompt_text=tailor_prompt,
                max_attempts=2,
                default_fallback=base_profile
            )
            return tailored_profile
        except Exception as e:
            logger.error(f"Tailoring failed, returning base profile: {e}")
            return base_profile
