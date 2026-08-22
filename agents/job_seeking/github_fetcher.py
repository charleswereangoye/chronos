import os
import requests
import logging

logger = logging.getLogger(__name__)

class GithubFetcher:
    def __init__(self, pat: str = None):
        self.pat = pat or os.getenv("GITHUB_PAT")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.pat:
            self.headers["Authorization"] = f"token {self.pat}"

    def fetch_user_data(self):
        """Fetches repos (public and private) and aggregates skills."""
        if not self.pat:
            logger.warning("No GITHUB_PAT provided. Cannot fetch private repos.")
        
        try:
            # If PAT is available, fetch authenticated user's repos
            if self.pat:
                url = "https://api.github.com/user/repos?sort=updated&per_page=100"
            else:
                return {"error": "GITHUB_PAT is required to fetch repos for the active user."}
            
            response = requests.get(url, headers=self.headers)
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
                    "private": repo.get("private"),
                    "stars": repo.get("stargazers_count", 0)
                })
            
            # Sort projects by stars
            projects.sort(key=lambda x: x["stars"], reverse=True)
            
            return {
                "top_languages": sorted(languages.items(), key=lambda x: x[1], reverse=True),
                "top_projects": projects[:5],
                "total_repos": len(projects)
            }
        except Exception as e:
            logger.error(f"Failed to fetch GitHub data: {e}")
            return {"error": str(e)}
