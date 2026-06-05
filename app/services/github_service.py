import httpx
import logging
from typing import Optional
from app.models.github_event import PRWebhookPayload

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubService:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> Optional[str]:
        """Fetch raw diff dari sebuah Pull Request."""
        url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}"
        diff_headers = {**self.headers, "Accept": "application/vnd.github.diff"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=diff_headers, timeout=30)

        if response.status_code != 200:
            logger.error(f"Failed to fetch diff: {response.status_code} - {response.text}")
            return None

        return response.text

    async def post_comment(self, repo_full_name: str, pr_number: int, body: str) -> bool:
        """Post review comment ke PR."""
        url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments"
        json_headers = {**self.headers, "Accept": "application/vnd.github+json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=json_headers,
                json={"body": body},
                timeout=30
            )

        if response.status_code == 201:
            logger.info(f"Comment posted to PR #{pr_number}")
            return True

        logger.error(f"Failed to post comment: {response.status_code} - {response.text}")
        return False

    def build_pr_context(self, payload: PRWebhookPayload, diff: str) -> dict:
        """Gabungkan metadata PR dan diff menjadi context object."""
        pr = payload.pull_request
        return {
            "repo": payload.repository.full_name,
            "pr_number": pr.number,
            "title": pr.title,
            "description": pr.body or "(no description)",
            "author": pr.user.login,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "diff": diff,
        }
