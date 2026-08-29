import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from agents.job_seeking.github_fetcher import GithubFetcher
from agents.job_seeking.linkedin_scraper import LinkedinScraper
from agents.job_seeking.resume_parser import ResumeParser
from shared.llm import generate_json_with_failover

logger = logging.getLogger("ProfileSynthesizer")

CACHE_TTL_HOURS = 6

DEFAULT_CONTACT = {
    "name": "Charles Were Angoye",
    "email": "charleswereangoye@gmail.com",
    "phone": "KE: +254 719 403 678 | RW: +250 795 589 824",
    "location": "Kigali, Rwanda / Nairobi, Kenya (GMT+2 / EAT)",
    "portfolio": "charleswereangoye.dev",
    "github": "github.com/charleswereangoye",
    "linkedin": "linkedin.com/in/charles-were-angoye-21a661326"
}

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
                        synthesized_at_str = data.get("synthesized_at")
                        if synthesized_at_str:
                            try:
                                synth_time = datetime.fromisoformat(synthesized_at_str)
                                if datetime.now() - synth_time < timedelta(hours=CACHE_TTL_HOURS):
                                    logger.info("Loaded fresh base candidate profile from cache.")
                                    return self._ensure_contact_fields(data)
                                else:
                                    logger.info("Profile cache has expired (> 6 hours). Refreshing...")
                                    return None
                            except Exception:
                                pass
                        return self._ensure_contact_fields(data)
            except Exception as e:
                logger.warning(f"Failed to read cache file: {e}")
        return None

    def _ensure_contact_fields(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in DEFAULT_CONTACT.items():
            if not profile.get(k):
                profile[k] = v
        return profile

    def _save_cached_profile(self, profile_data: Dict[str, Any]):
        try:
            profile_data["synthesized_at"] = datetime.now().isoformat()
            profile_data = self._ensure_contact_fields(profile_data)
            temp_file = os.path.join(self.state_dir, f".tmp_cache_{os.getpid()}.json")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=4)
            os.replace(temp_file, self.cache_file)
            logger.info("Saved base candidate profile to cache.")
        except Exception as e:
            logger.error(f"Failed to save profile cache: {e}")

    async def get_base_profile(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Gets or builds the master base profile dynamically from Resume, GitHub, and LinkedIn."""
        if not force_refresh:
            cached = self._load_cached_profile()
            if cached:
                return cached

        logger.info("Gathering live candidate data from LinkedIn, GitHub, and Resume...")
        resume_text = self.resume.extract_text()
        github_data = self.github.fetch_user_data()
        linkedin_data = await self.linkedin.scrape_profile()

        prompt = f"""
You are an expert technical talent agent and recruiter.
Analyze the candidate's real-time data from LinkedIn, GitHub, and Resume to dynamically construct an accurate, up-to-date master candidate profile.

CRITICAL INSTRUCTIONS:
1. LIVE DATA IS THE AUTHORITATIVE SOURCE OF TRUTH:
   - Always prioritize live LinkedIn data and GitHub repository activities for current title, current employer/role, graduation status, and newest technical skills.
   - If LinkedIn shows a new position (e.g. starting at a new company or moving from an intern to a full-time engineer), immediately reflect that new role at the top of the `experience` list and update `title` and `seniority_level`.
   - If GitHub shows newly created repositories, languages, or architectural stacks, dynamically incorporate those verified skills into the profile.
   - Use the base resume as a foundational reference for historical project context and education credentials.
2. DYNAMICALLY DERIVE SENIORITY & STATUS:
   - Determine the candidate's professional level (intern, entry-level, junior, mid-level, or senior) strictly from their live LinkedIn headline/experience and GitHub activity.
3. EXTRACT VERIFIED SKILLS, EXPERIENCES & TECHNICAL PROJECTS:
   - Extract verified languages, frameworks, databases, and DevOps tools directly from GitHub repositories and LinkedIn skills.
   - Extract professional experiences and technical projects (e.g. Trajour, InternLink, Chronos, Personal Portfolio at charleswereangoye.dev).
4. PRESERVE DUAL CONTACT INFORMATION:
   - Phone must include both Kenyan and Rwandan numbers: "KE: +254 719 403 678 | RW: +250 795 589 824"
   - Location: "Kigali, Rwanda / Nairobi, Kenya (GMT+2 / EAT)"
   - Portfolio: "charleswereangoye.dev"
5. ABSOLUTELY NO em-dashes (—). Use standard hyphens (-) or colons (:).
6. Return ONLY valid JSON matching this schema:

{{
    "name": "Charles Were Angoye",
    "title": "Current Professional Title (e.g. Full-Stack Software Engineer or Software Engineering Student)",
    "seniority_level": "intern | entry-level | junior | mid-level | senior",
    "current_status": "Concise 1-sentence description of current educational/employment status",
    "email": "charleswereangoye@gmail.com",
    "phone": "KE: +254 719 403 678 | RW: +250 795 589 824",
    "location": "Kigali, Rwanda / Nairobi, Kenya (GMT+2 / EAT)",
    "portfolio": "charleswereangoye.dev",
    "github": "github.com/charleswereangoye",
    "linkedin": "linkedin.com/in/charles-were-angoye-21a661326",
    "target_company": "",
    "summary": "A powerful 2-3 sentence professional summary highlighting core strengths and full-stack capabilities.",
    "skills": ["JavaScript", "TypeScript", "Python", "React", "Next.js", "Flask", "Node.js", "PostgreSQL", "Docker", "REST APIs", "Tailwind CSS"],
    "experience": [
        {{
            "role": "Backend Developer Intern & Team Lead",
            "company": "Infinity Innovations Co.",
            "duration": "May 2026 - Present",
            "highlights": [
                "Led backend development workflows, assigning daily tasks and performing rigorous code reviews to maintain repository stability.",
                "Engineered scalable RESTful API endpoints and optimized database schemas in Python and PostgreSQL for low-latency client requests."
            ]
        }}
    ],
    "projects": [
        {{
            "name": "Trajour: Forex Trading Journal & Analytics Dashboard",
            "role": "Full-Stack Developer & UI Designer",
            "stack": "Next.js, React, PostgreSQL, Supabase, Tailwind CSS",
            "highlights": [
                "Architected a data-dense financial journal to log trade setups, pattern metrics, and personal psychology data.",
                "Integrated PostgreSQL with Supabase for relational trade data and engineered a high-performance analytics UI."
            ]
        }},
        {{
            "name": "InternLink: Student & SME Discovery Portal",
            "role": "Backend Developer",
            "stack": "Python, Flask, Cloud SQL, Chart.js, REST APIs",
            "highlights": [
                "Built a skill-based candidate matching system and integrated Chart.js for visualization dashboards.",
                "Migrated relational database infrastructure from SQLite to Cloud SQL for enhanced security and scalability."
            ]
        }},
        {{
            "name": "Chronos: Autonomous Multi-Agent Operating System",
            "role": "Lead Architect & Systems Engineer",
            "stack": "Python, Podman/Docker, Playwright, Gemini LLMs, Telegram API",
            "highlights": [
                "Engineered a containerized multi-agent system executing autonomous job radar, CV tailoring, and browser workflows.",
                "Implemented resilient LLM failover, API load-balancing, and asynchronous message dispatching via Telegram."
            ]
        }},
        {{
            "name": "Personal Developer Portfolio",
            "role": "Full-Stack Developer",
            "stack": "Next.js, React, TypeScript, Tailwind CSS, Framer Motion",
            "highlights": [
                "Deployed high-performance developer portfolio at charleswereangoye.dev with dark/light themes and fluid micro-interactions.",
                "Optimized asset loading, site architecture, and technical SEO for 100% Lighthouse performance scores."
            ]
        }}
    ],
    "education": [
        {{
            "degree": "Bachelor of Science in Software Engineering",
            "institution": "The African Leadership University (ALU)",
            "location": "Kigali, Rwanda",
            "year": "Jan 2025 - Expected Jan 2028"
        }},
        {{
            "degree": "International Certificate of Digital Literacy (ICDL)",
            "institution": "Computer Pride",
            "location": "Nairobi, Kenya",
            "year": "May 2024 - Sep 2024"
        }}
    ]
}}

LIVE CANDIDATE DATA:
--- LINKEDIN ---
{json.dumps(linkedin_data, indent=2)}

--- GITHUB ---
{json.dumps(github_data, indent=2)}

--- RESUME ---
{resume_text if resume_text else "No local base resume PDF supplied. Derive strictly from LinkedIn & GitHub."}
"""
        fallback_profile = {
            "name": "Charles Were Angoye",
            "title": "Full-Stack Software Engineer",
            "seniority_level": "junior",
            "current_status": "Software Engineering Student & Full-Stack Developer",
            "email": "charleswereangoye@gmail.com",
            "phone": "KE: +254 719 403 678 | RW: +250 795 589 824",
            "location": "Kigali, Rwanda / Nairobi, Kenya (GMT+2 / EAT)",
            "portfolio": "charleswereangoye.dev",
            "github": "github.com/charleswereangoye",
            "linkedin": "linkedin.com/in/charles-were-angoye-21a661326",
            "summary": "Full-Stack Software Engineer specializing in modern React/Next.js frontends, Python/Flask backends, PostgreSQL databases, and containerized Docker environments.",
            "skills": ["JavaScript (ES6+)", "TypeScript", "Python (Flask / FastAPI)", "React", "Next.js", "Tailwind CSS", "Node.js", "PostgreSQL", "Supabase", "Docker", "REST APIs", "Linux (Arch/CachyOS)"],
            "experience": [
                {
                    "role": "Backend Developer Intern & Team Lead",
                    "company": "Infinity Innovations Co.",
                    "duration": "May 2026 - Present",
                    "highlights": [
                        "Stepped up as the backend team lead, assigning daily tasks and conducting code reviews to maintain repository stability.",
                        "Architected scalable RESTful API endpoints and optimized database schemas in Python and PostgreSQL."
                    ]
                }
            ],
            "projects": [
                {
                    "name": "Trajour: Forex Trading Journal & Analytics Dashboard",
                    "role": "Full-Stack Developer & UI Designer",
                    "stack": "Next.js, React, PostgreSQL, Supabase, Tailwind CSS",
                    "highlights": [
                        "Architected a custom data-dense financial journal to log trade setups and pattern metrics.",
                        "Integrated PostgreSQL with Supabase to manage relational financial data securely."
                    ]
                },
                {
                    "name": "Chronos: Autonomous Multi-Agent Operating System",
                    "role": "Lead Architect & Systems Engineer",
                    "stack": "Python, Podman, Playwright, Gemini LLMs",
                    "highlights": [
                        "Architected autonomous multi-agent orchestration pipelines using Python, Podman, and Playwright for real-time workflows."
                    ]
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Science in Software Engineering",
                    "institution": "The African Leadership University (ALU)",
                    "location": "Kigali, Rwanda",
                    "year": "Jan 2025 - Expected Jan 2028"
                }
            ]
        }

        try:
            profile = generate_json_with_failover(
                prompt_text=prompt,
                max_attempts=3,
                default_fallback=fallback_profile
            )
            profile = self._ensure_contact_fields(profile)
            self._save_cached_profile(profile)
            return profile
        except Exception as e:
            logger.error(f"Failed to synthesize profile: {e}")
            return self._ensure_contact_fields(fallback_profile)

    async def synthesize(self, job_description: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        """Synthesizes candidate profile, tailoring it specifically to a target job description."""
        base_profile = await self.get_base_profile(force_refresh=force_refresh)
        
        if not job_description or not job_description.strip():
            return base_profile

        logger.info("Tailoring candidate profile to target job description...")
        tailor_prompt = f"""
You are an expert technical resume strategist.
Tailor the candidate's JSON profile to align directly with the target job requirements below.

CRITICAL INSTRUCTIONS:
1. KEEP THE PROFILE AUTHENTIC: Emphasize real skills ({', '.join(base_profile.get('skills', []))}) matching the job description without fabricating unearned experience.
2. ABSOLUTELY NO em-dashes (—).
3. Align `summary`, `skills`, `experience.highlights`, and `projects` to the tech stack in the job description.
4. Extract `target_company` accurately.
5. Return ONLY valid JSON matching the schema.

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
            # Guarantee identity & contact info is always fully preserved
            return self._ensure_contact_fields(tailored_profile)
        except Exception as e:
            logger.error(f"Tailoring failed, returning base profile: {e}")
            return base_profile
