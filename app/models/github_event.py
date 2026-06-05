from pydantic import BaseModel
from typing import Optional


class GitHubUser(BaseModel):
    login: str
    id: int


class GitHubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    html_url: str
    default_branch: str


class GitHubBranch(BaseModel):
    label: str
    ref: str
    sha: str


class PullRequest(BaseModel):
    number: int
    title: str
    body: Optional[str] = None
    state: str
    html_url: str
    user: GitHubUser
    head: GitHubBranch
    base: GitHubBranch
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0


class PRWebhookPayload(BaseModel):
    action: str
    number: int
    pull_request: PullRequest
    repository: GitHubRepo
    sender: GitHubUser
