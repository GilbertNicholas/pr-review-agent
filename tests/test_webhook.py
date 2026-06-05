import hashlib
import hmac
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

MOCK_SECRET = "test_secret"

SAMPLE_PAYLOAD = {
    "action": "opened",
    "number": 1,
    "pull_request": {
        "number": 1,
        "title": "Add new feature",
        "body": "This PR adds a new feature",
        "state": "open",
        "html_url": "https://github.com/test/repo/pull/1",
        "user": {"login": "testuser", "id": 1},
        "head": {"label": "testuser:feature", "ref": "feature", "sha": "abc123"},
        "base": {"label": "testuser:main", "ref": "main", "sha": "def456"},
        "additions": 10,
        "deletions": 2,
        "changed_files": 1
    },
    "repository": {
        "id": 1,
        "name": "repo",
        "full_name": "testuser/repo",
        "html_url": "https://github.com/testuser/repo",
        "default_branch": "main"
    },
    "sender": {"login": "testuser", "id": 1}
}


def make_signature(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_ignores_non_pr_event():
    response = client.post(
        "/webhook",
        json={"action": "created"},
        headers={"X-GitHub-Event": "push"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_ignores_non_reviewable_action():
    payload = {**SAMPLE_PAYLOAD, "action": "closed"}
    response = client.post(
        "/webhook",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_accepts_opened_pr(monkeypatch):
    # Mock background task agar tidak benar-benar call GitHub API
    monkeypatch.setattr(
        "app.routers.webhook.process_pr_review",
        lambda payload: None
    )
    response = client.post(
        "/webhook",
        json=SAMPLE_PAYLOAD,
        headers={"X-GitHub-Event": "pull_request"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["pr"] == 1
