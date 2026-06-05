# PR Review Agent

An AI-powered GitHub Pull Request reviewer built with FastAPI and Claude.

When a PR is opened or updated, this agent automatically fetches the diff, sends it to Claude for analysis, and posts a structured review comment directly on the PR.

## How it works

```
GitHub PR opened/updated
        ↓
  Webhook received (FastAPI)
        ↓
  Signature verified (HMAC-SHA256)
        ↓
  Diff fetched (GitHub API)
        ↓
  AI Review generated (Claude)
        ↓
  Comment posted to PR (GitHub API)
```

## Tech Stack

- **Python 3.12** + **FastAPI** — webhook server
- **Anthropic Claude** — AI review engine
- **GitHub API** — fetch diffs, post comments
- **Docker** — containerized deployment
- **Coolify** on **Hetzner VPS** — self-hosted infrastructure

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/yourusername/pr-review-agent
cd pr-review-agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your actual keys
```

| Variable | Description |
|---|---|
| `GITHUB_WEBHOOK_SECRET` | Secret set in GitHub webhook settings |
| `GITHUB_TOKEN` | Personal Access Token with `repo` scope |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

### 3. Run locally

```bash
uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`

### 4. Set up GitHub webhook

In your repo settings → Webhooks → Add webhook:
- **Payload URL:** `https://your-domain.com/webhook`
- **Content type:** `application/json`
- **Secret:** same as `GITHUB_WEBHOOK_SECRET`
- **Events:** Pull requests only

### 5. Deploy with Docker

```bash
docker build -t pr-review-agent .
docker run -d --env-file .env -p 8000:8000 pr-review-agent
```

## Running tests

```bash
pytest tests/ -v
```

## Example review output

```markdown
## ✅ AI Code Review — Approved

### Summary
This PR adds a new authentication middleware with proper error handling...

### What's Good
- ✨ Clean separation of concerns
- ✨ Good use of async/await patterns

### Suggestions
- 💡 Consider adding rate limiting to the login endpoint
```

---

Built by [Gilbert](https://opreklabs.com) · Part of AI Automation Portfolios
