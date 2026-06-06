import hashlib
import hmac
import json
import logging
import os
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from app.models.github_event import PRWebhookPayload
from app.services.github_service import GitHubService
from app.services.review_service import ReviewService

load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Actions yang akan di-trigger review
REVIEWABLE_ACTIONS = {"opened", "synchronize", "reopened"}


def verify_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Verifikasi GitHub webhook signature menggunakan HMAC-SHA256."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


async def process_pr_review(payload: PRWebhookPayload):
    """Background task: fetch diff, generate review, post comment."""
    pr = payload.pull_request
    repo = payload.repository.full_name

    logger.info(f"Processing review for {repo} PR #{pr.number}: {pr.title}")

    github = GitHubService(token=GITHUB_TOKEN)
    reviewer = ReviewService(api_key=ANTHROPIC_API_KEY)

    # PR size guard
    total_lines = pr.additions + pr.deletions
    if pr.changed_files > 50 or total_lines > 5000:
        logger.info(f"PR #{pr.number} too large ({pr.changed_files} files, {total_lines} lines) — skipping review")
        body = (
            f"## ⚠️ AI Code Review — PR Too Large\n"
            f"*Reviewed by PR Review Agent · PR #{pr.number}*\n\n"
            f"This PR is too large for automated review:\n"
            f"- **{pr.changed_files} files changed** (limit: 50)\n"
            f"- **{total_lines} lines changed** (limit: 5,000)\n\n"
            f"Consider breaking this PR into smaller, focused changes.\n\n"
            f"---\n*This review was generated automatically by an AI agent.*"
        )
        await github.post_comment(repo, pr.number, body)
        return

    # 1. Fetch diff
    diff = await github.get_pr_diff(repo, pr.number)
    if not diff:
        logger.error(f"Could not fetch diff for PR #{pr.number}")
        return

    # 2. Build context
    context = github.build_pr_context(payload, diff)

    # 3. Generate AI review
    review = reviewer.generate_review(context)

    # 4. Format ke Markdown
    comment_body = reviewer.format_as_markdown(review, context)

    # 5. Post comment ke GitHub
    await github.post_comment(repo, pr.number, comment_body)


@router.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Menerima GitHub webhook event dan trigger AI review untuk PR events."""
    payload_bytes = await request.body()

    # Verifikasi signature (skip jika secret belum di-set, untuk development)
    if WEBHOOK_SECRET:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(payload_bytes, signature):
            logger.warning("Invalid webhook signature received")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Hanya handle pull_request events
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "pull_request":
        logger.info(f"Ignoring non-PR event: {event_type}")
        return {"status": "ignored", "reason": f"event type '{event_type}' not handled"}

    # Parse payload
    try:
        payload_dict = json.loads(payload_bytes)
        payload = PRWebhookPayload(**payload_dict)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=422, detail="Invalid payload format")

    # Hanya process action yang relevan
    if payload.action not in REVIEWABLE_ACTIONS:
        logger.info(f"Ignoring PR action: {payload.action}")
        return {"status": "ignored", "reason": f"action '{payload.action}' not reviewable"}

    logger.info(f"Queuing review for PR #{payload.number} ({payload.action})")

    # Jalankan review di background agar webhook tidak timeout
    background_tasks.add_task(process_pr_review, payload)

    return {
        "status": "accepted",
        "pr": payload.number,
        "action": payload.action,
        "message": "Review queued"
    }
