import os
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger("GithubFetcher")

class GithubFetcher:
    def __init__(self, pat: str = None):
        self.pat = pat or os.getenv("GITHUB_PAT")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.pat:
            self.headers["Authorization"] = f"token {self.pat}"

    def fetch_user_data(self) -> Dict[str, Any]:
        """Fetches user profile metadata, repositories, and language statistics."""
        if not self.pat:
            logger.warning("No GITHUB_PAT provided. GitHub data will be limited.")
            return {"error": "GITHUB_PAT is required to fetch repos for the active user."}
        
        try:
            # 1. Fetch user profile
            user_profile = {}
            try:
                user_resp = requests.get("https://api.github.com/user", headers=self.headers, timeout=10)
                if user_resp.status_code == 200:
                    u = user_resp.json()
                    user_profile = {
                        "login": u.get("login"),
                        "name": u.get("name"),
                        "bio": u.get("bio"),
                        "company": u.get("company"),
                        "location": u.get("location"),
                        "blog": u.get("blog"),
                        "public_repos": u.get("public_repos", 0),
                        "hireable": u.get("hireable")
                    }
            except Exception as pe:
                logger.warning(f"Failed to fetch GitHub profile endpoint: {pe}")

            # 2. Fetch repos
            url = "https://api.github.com/user/repos?sort=updated&per_page=100"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            repos = response.json()
            
            languages = {}
            projects = []
            
            for repo in repos:
                if repo.get("fork"):
                    continue # Skip forks
                
                lang = repo.get("language")
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1
                    
                projects.append({
                    "name": repo.get("name"),
                    "description": repo.get("description"),
                    "url": repo.get("html_url"),
                    "language": lang,
                    "topics": repo.get("topics", []),
                    "private": repo.get("private"),
                    "stars": repo.get("stargazers_count", 0),
                    "updated_at": repo.get("updated_at")
                })
            
            # Sort projects by stars and recent activity
            projects.sort(key=lambda x: (x["stars"], x.get("updated_at") or ""), reverse=True)
            
            return {
                "profile": user_profile,
                "top_languages": sorted(languages.items(), key=lambda x: x[1], reverse=True),
                "top_projects": projects[:8],
                "total_repos": len(projects)
            }
        except Exception as e:
            logger.error(f"Failed to fetch GitHub data: {e}")
            return {"error": str(e)}
