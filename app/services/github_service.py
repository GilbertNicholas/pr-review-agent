import httpx
import logging
import re
from typing import Optional
from app.models.github_event import PRWebhookPayload

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"

SKIP_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", "composer.lock",
    "Gemfile.lock", "go.sum", "go.mod",
}

SKIP_EXTENSIONS = {".min.js", ".min.css", ".map", ".snap"}

SKIP_PATTERNS = re.compile(r'\.(generated|pb\.go|pb2\.py|pb\.ts)$')


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

        return self.filter_diff(response.text)

    def filter_diff(self, raw_diff: str) -> str:
        """Buang file yang tidak relevan dari diff (lock files, minified, generated)."""
        sections = re.split(r'(?=^diff --git )', raw_diff, flags=re.MULTILINE)
        kept = []

        for section in sections:
            if not section.startswith("diff --git"):
                kept.append(section)
                continue

            match = re.match(r'^diff --git a/(.+?) b/(.+)', section)
            if not match:
                kept.append(section)
                continue

            filename = match.group(2)
            basename = filename.split("/")[-1]

            if basename in SKIP_FILENAMES:
                logger.info(f"Skipping diff for: {filename} (lock/generated file)")
                continue

            if any(basename.endswith(ext) for ext in SKIP_EXTENSIONS):
                logger.info(f"Skipping diff for: {filename} (minified/map file)")
                continue

            if SKIP_PATTERNS.search(filename):
                logger.info(f"Skipping diff for: {filename} (generated file pattern)")
                continue

            kept.append(section)

        return "".join(kept)

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
