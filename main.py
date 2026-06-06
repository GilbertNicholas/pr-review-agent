from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import webhook
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PR Review Agent starting up...")
    yield
    logger.info("PR Review Agent shutting down...")


app = FastAPI(
    title="PR Review Agent",
    description="AI-powered GitHub Pull Request reviewer",
    version="1.1.0",
    lifespan=lifespan
)

app.include_router(webhook.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pr-review-agent"}
