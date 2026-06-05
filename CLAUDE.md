# CLAUDE.md — PR Review Agent
> Dokumen ini adalah panduan lengkap untuk Claude Code agar memahami project, status saat ini, dan next steps yang harus dikerjakan.

---

## Apa project ini?

**PR Review Agent** adalah service berbasis Python + FastAPI yang secara otomatis mereview GitHub Pull Request menggunakan AI (Claude/Anthropic).

**Flow utama:**
```
Developer buka PR di GitHub
    → GitHub kirim webhook event ke service ini
    → Service fetch diff dari PR via GitHub API
    → Diff dikirim ke Claude untuk di-review
    → Hasil review di-format sebagai Markdown
    → Review di-post sebagai comment di PR
```

**Tujuan project:** Portfolio untuk rebranding sebagai AI Automation/AI Architect, ditargetkan untuk remote job hunting di luar negeri.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI + Uvicorn |
| HTTP client | httpx (async) |
| AI provider | Anthropic (claude-haiku-4-5-20251001) |
| GitHub integration | httpx (direct REST API calls) |
| Data validation | Pydantic v2 |
| Deployment | Docker → Coolify → Hetzner VPS (CX33, Nuremberg) |
| DNS/SSL | Cloudflare → Traefik (via Coolify) |

---

## Struktur Project

```
pr-review-agent/
├── main.py                         # Entry point FastAPI app + lifespan + health check
├── requirements.txt                # Dependencies
├── Dockerfile                      # Production Docker image
├── .env.example                    # Template environment variables
├── .gitignore
├── README.md
├── CLAUDE.md                       # File ini — context untuk Claude Code
│
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── github_event.py         # Pydantic models: PRWebhookPayload, PullRequest, dll
│   ├── routers/
│   │   ├── __init__.py
│   │   └── webhook.py              # POST /webhook — endpoint utama
│   └── services/
│       ├── __init__.py
│       ├── github_service.py       # Fetch diff + post comment via GitHub API
│       └── review_service.py       # AI review engine + Markdown formatter
│
└── tests/
    ├── __init__.py
    └── test_webhook.py             # 4 test cases (semua passing)
```

---

## Environment Variables

File `.env` harus dibuat dari `.env.example`. Isi dengan nilai nyata:

```env
GITHUB_WEBHOOK_SECRET=    # Secret yang di-set di GitHub webhook settings
GITHUB_TOKEN=             # GitHub Personal Access Token (scope: repo)
ANTHROPIC_API_KEY=        # Anthropic API key
APP_ENV=development       # atau production
LOG_LEVEL=INFO
```

**Cara buat GitHub Token:**
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → centang scope: `repo` (full control)
3. Copy token → paste ke `GITHUB_TOKEN`

**Cara buat Webhook Secret:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Cara Jalankan Locally

```bash
# 1. Install dependencies
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Setup env
cp .env.example .env
# Edit .env dengan nilai nyata

# 3. Run server
uvicorn main:app --reload --port 8000

# 4. Run tests
pytest tests/ -v

# 5. Cek API docs (auto-generated FastAPI)
# Buka browser: http://localhost:8000/docs
```

**Untuk test webhook secara lokal**, gunakan ngrok atau cloudflared:
```bash
cloudflared tunnel --url http://localhost:8000
# Copy URL yang diberikan → paste ke GitHub webhook settings
```

---

## Cara Deploy ke Hetzner via Coolify

Sama persis dengan project sebelumnya (n8n, CS Ticket Triage):

```bash
# 1. Push ke GitHub
git init
git add .
git commit -m "feat: initial PR Review Agent"
git remote add origin https://github.com/username/pr-review-agent
git push -u origin main

# 2. Di Coolify dashboard:
#    - New Resource → Public Repository
#    - Paste GitHub repo URL
#    - Build pack: Dockerfile
#    - Set environment variables (dari .env)
#    - Set domain: pr-agent.opreklabs.com (atau subdomain lain)
#    - Deploy

# 3. Setelah deploy, tambahkan webhook di GitHub:
#    Repo Settings → Webhooks → Add webhook
#    Payload URL: https://pr-agent.opreklabs.com/webhook
#    Content type: application/json
#    Secret: nilai GITHUB_WEBHOOK_SECRET
#    Events: Let me select → Pull requests
```

---

## Status Saat Ini (Fase 1 — SELESAI)

Semua yang ada di zip ini sudah complete dan tested:

- [x] FastAPI project structure
- [x] POST /webhook endpoint
- [x] GitHub webhook signature verification (HMAC-SHA256)
- [x] Filter event: hanya handle `pull_request` dengan action `opened/synchronize/reopened`
- [x] Pydantic models untuk GitHub payload
- [x] GitHub service: fetch diff + post comment
- [x] AI review engine: generate review via Claude
- [x] Markdown formatter: format review jadi comment GitHub
- [x] Background task: proses review tanpa block webhook response
- [x] Dockerfile untuk deployment
- [x] 4 unit tests (semua passing)
- [x] README dokumentasi

---

## Next Steps — Yang Harus Dikerjakan

### IMMEDIATE: Setup & Deploy (bukan coding, tapi wajib dulu)

```
1. Isi file .env dengan 3 keys nyata
2. Buat dummy repo GitHub untuk testing
3. Push project ke GitHub
4. Deploy ke Coolify (Hetzner VPS)
5. Daftarkan webhook di dummy repo
6. Buka PR pertama → verifikasi agent bekerja
```

### Fase 2 — Peningkatan Kualitas Review

Setelah basic flow berjalan, improve kualitas review dengan:

**2a. Smarter diff parsing**
- Skip file yang tidak relevan: `package-lock.json`, `*.min.js`, `*.generated.*`, binary files
- Prioritaskan file penting: `*.py`, `*.ts`, `*.go`, business logic files
- Implementasi di: `app/services/github_service.py` → tambah method `filter_diff()`

**2b. Per-file review**
- Saat ini: seluruh diff dikirim sebagai satu prompt (bisa token limit jika PR besar)
- Target: review per file, aggregate hasilnya
- Implementasi di: `app/services/review_service.py` → tambah method `review_by_file()`

**2c. Inline PR comments**
- Saat ini: post satu comment di level PR (issue comment)
- Target: post comment di baris kode spesifik (review comment)
- GitHub API endpoint berbeda: `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews`
- Ini jauh lebih impressive untuk demo dan portfolio

**2d. PR size guard**
- Jika PR terlalu besar (misal >50 files atau >5000 lines), post comment bahwa PR terlalu besar untuk di-review otomatis
- Implementasi di: `app/routers/webhook.py` → cek `pr.changed_files` dan `pr.additions + pr.deletions`

### Fase 3 — Features Tambahan (Portfolio Polish)

**3a. Review summary label**
- Auto-assign GitHub label ke PR berdasarkan verdict
- `approved` → label `ai-approved` (hijau)
- `request_changes` → label `ai-needs-work` (merah)
- GitHub API: `PATCH /repos/{owner}/{repo}/issues/{issue_number}/labels`

**3b. Re-review on push**
- Saat ini sudah handle `synchronize` action (push baru ke PR yang ada)
- Tambahkan: hapus comment review lama sebelum post yang baru
- Simpan `comment_id` di memory/state sederhana (dict in-memory cukup untuk MVP)

**3c. Statistics endpoint**
- `GET /stats` → return berapa PR yang sudah di-review, breakdown verdict, dll
- Simpan di in-memory counter (tidak perlu database untuk MVP)
- Ini bagus untuk demo: "agent sudah review X PRs"

**3d. Webhook dashboard (opsional)**
- Simple HTML page di `/` yang menampilkan recent reviews
- Bisa pakai Jinja2 template atau return static HTML
- Bagus untuk screenshot di LinkedIn

### Fase 4 — Polish & Launch

**4a. Improve system prompt**
- Test dengan berbagai jenis PR (feature, bugfix, refactor, docs)
- Tune prompt berdasarkan kualitas output yang dihasilkan
- Pertimbangkan: language-specific prompts (Python vs JS vs Go)

**4b. Error handling & resilience**
- Retry logic jika GitHub API rate limited (429)
- Graceful handling jika Anthropic API down
- Dead letter: log failed reviews ke file untuk debugging

**4c. Dokumentasi & demo**
- Record demo video: buka PR → tunggu → review muncul
- Screenshot before/after (PR tanpa review vs dengan review)
- Update README dengan arsitektur diagram

**4d. LinkedIn post**
- Framing: "Built an AI agent that reviews my code automatically"
- Tampilkan screenshot review yang dihasilkan
- Jelaskan tech stack dan arsitektur

---

## Cara Claude AI Dipanggil (Detail Teknis)

File: `app/services/review_service.py`

```python
# Model yang digunakan
model = "claude-haiku-4-5-20251001"   # Haiku untuk dev (murah)
                                        # Ganti ke claude-sonnet-4-6 untuk production

# System prompt fokus pada:
# - Code quality & readability
# - Potential bugs
# - Security vulnerabilities
# - Performance
# - Best practices

# Output format: JSON structured
# {
#   "overall_summary": str,
#   "verdict": "approve" | "request_changes" | "comment",
#   "critical_issues": [{"description": str, "severity": "high"|"medium"|"low"}],
#   "suggestions": [{"description": str}],
#   "positive_notes": [str]
# }

# Diff dibatasi 12.000 karakter untuk menghindari token limit
# Jika lebih besar → di-truncate dengan notice
```

---

## Endpoints yang Tersedia

| Method | Path | Deskripsi |
|---|---|---|
| `GET` | `/health` | Health check — return `{"status": "ok"}` |
| `POST` | `/webhook` | Menerima GitHub webhook event |
| `GET` | `/docs` | Auto-generated Swagger UI (FastAPI) |
| `GET` | `/redoc` | ReDoc API documentation |

---

## Contoh Output Review Agent

Ini contoh comment yang akan dipost ke GitHub PR:

```markdown
## ✅ AI Code Review — Approved
*Reviewed by PR Review Agent · PR #12*

### Summary
This PR adds a new user authentication middleware with JWT validation.
The implementation is clean and follows existing patterns in the codebase.

### Issues Found
- 🟡 **Medium:** JWT secret is hardcoded as a fallback value in line 34.
  Consider requiring the env var and failing fast if not set.
- 🔵 **Low:** Missing docstring on the `validate_token()` function.

### Suggestions
- 💡 Consider adding rate limiting to the `/login` endpoint to prevent brute force
- 💡 Add integration test for expired token scenario

### What's Good
- ✨ Clean separation of concerns — middleware is properly isolated
- ✨ Good use of async/await throughout

---
*This review was generated automatically by an AI agent. Use your own judgment.*
```

---

## Known Limitations & Notes

- **Token limit:** Diff dibatasi 12.000 karakter. PR yang sangat besar akan di-truncate.
- **Rate limiting:** Belum ada retry logic untuk GitHub API 429. Tambahkan di Fase 3.
- **Stateless:** Service tidak menyimpan state. Setiap restart, history hilang.
- **Single model:** Menggunakan Haiku untuk efisiensi. Upgrade ke Sonnet untuk review lebih mendalam.
- **No database:** MVP intentionally tanpa database. Cukup untuk portfolio.
- **Background tasks:** Review dijalankan di background agar webhook tidak timeout (GitHub timeout 10 detik).

---

## Referensi

- [FastAPI docs](https://fastapi.tiangolo.com)
- [GitHub Webhooks docs](https://docs.github.com/en/webhooks)
- [GitHub REST API — Pull Requests](https://docs.github.com/en/rest/pulls)
- [Anthropic Python SDK](https://github.com/anthropic-ai/anthropic-sdk-python)
- [Coolify docs](https://coolify.io/docs)
