import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.backend import auth_backend, current_active_user, fastapi_users
from app.config import settings
from app.routers import campaigns
from app.routers import sync
from app.routers import products
from app.routers import ws
from app.routers import render
from app.routers import orchestrator
from app.routers import sections
from app.routers import settings as settings_router
from app.routers import banners
from app.routers import templates
from app.routers import themes
from app.routers import overrides
from app.routers import snapshots
from app.routers import audit
from app.routers import review
from app.routers import comments
from app.routers import approvals
from app.routers import preferences
from app.routers import chat
from app.routers import vibe_shift
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.ws.gateway import gateway

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: set up and tear down shared resources."""

    # ── Ensure static directories exist ───────────────────────────────────────
    Path("static/images").mkdir(parents=True, exist_ok=True)

    # ── Redis connection ───────────────────────────────────────────────────────
    redis_client = None
    try:
        import redis.asyncio as aioredis  # type: ignore[import]
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Verify connectivity
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("lifespan: Redis connected at %s", settings.redis_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "lifespan: Redis unavailable (%s) — sync status polling will use DB fallback", exc
        )
        app.state.redis = None

    # ── SKU cache ──────────────────────────────────────────────────────────────
    if redis_client is not None:
        try:
            from app.modules.sku_cache import SKUCache
            app.state.sku_cache = SKUCache(redis_client)
            logger.info("lifespan: SKUCache initialized")
        except Exception as exc:  # noqa: BLE001
            logger.warning("lifespan: SKUCache init failed (%s)", exc)
            app.state.sku_cache = None
    else:
        app.state.sku_cache = None

    # ── WebSocket gateway ──────────────────────────────────────────────────────
    app.state.gateway = gateway

    # ── ARQ pool ───────────────────────────────────────────────────────────────
    arq_pool = None
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        from app.workers.sync_worker import _parse_redis_url

        arq_pool = await create_pool(_parse_redis_url(settings.redis_url))
        app.state.arq_pool = arq_pool
        logger.info("lifespan: ARQ pool connected")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "lifespan: ARQ pool unavailable (%s) — background jobs will not be enqueued", exc
        )
        app.state.arq_pool = None

    yield  # application runs here

    # ── Teardown ───────────────────────────────────────────────────────────────
    if arq_pool is not None:
        try:
            await arq_pool.close()
        except Exception:  # noqa: BLE001
            pass

    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception:  # noqa: BLE001
            pass


app = FastAPI(
    title="Email Builder API",
    description="Dynamic Email Builder backend API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ───────────────────────────────────────────────────────────────
_static_dir = Path("static")
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Auth routes: POST /auth/jwt/login, POST /auth/jwt/logout
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Alias: POST /auth/login, POST /auth/logout (matches Issue 1 AC text)
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

# Registration: POST /auth/register
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# Password reset: POST /auth/forgot-password, POST /auth/reset-password
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# User management: GET/PATCH /users/me, GET/PATCH/DELETE /users/{id}
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Campaign CRUD
app.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])

# Google Sheets sync + products
app.include_router(sync.router, prefix="/campaigns", tags=["sync"])

# Product image management
app.include_router(products.router, prefix="/campaigns", tags=["products"])

# WebSocket endpoint: /ws/{campaign_id}
app.include_router(ws.router)

# Campaign render endpoint
app.include_router(render.router, tags=["render"])

# Visual orchestrator: brief generation + first-render
app.include_router(orchestrator.router, prefix="/campaigns", tags=["orchestrator"])

# Section locking
app.include_router(sections.router, prefix="/campaigns", tags=["sections"])

# Global settings + keyword mappings (Issue 23)
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])

# Banner generation (Issue 7)
app.include_router(banners.router, tags=["banners"])

# Template catalogue (Issue 8)
app.include_router(templates.router, tags=["templates"])

# Theme catalogue (Issue 9)
app.include_router(themes.router, tags=["themes"])

# Manual overrides (Issues 11 + 12)
app.include_router(overrides.router, tags=["overrides"])

# Snapshots (Issue 16)
app.include_router(snapshots.router, tags=["snapshots"])

# Pre-flight audit (Issue 19)
app.include_router(audit.router, tags=["audit"])

# Review share link (Issue 20)
app.include_router(review.router, tags=["review"])

# Reviewer comments (Issue 21)
app.include_router(comments.router, tags=["comments"])

# Reviewer approval (Issue 22)
app.include_router(approvals.router, tags=["approvals"])

# User preference memory (Issue 17)
app.include_router(preferences.router, tags=["preferences"])

# AI chat engine (Issue 14)
app.include_router(chat.router, tags=["chat"])

# Vibe Shift (Issue 15)
app.include_router(vibe_shift.router, tags=["vibe-shift"])


@app.get("/auth/me", response_model=UserRead, tags=["auth"])
async def get_me(user=Depends(current_active_user)):
    return user


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "emailer-builder-api"}
