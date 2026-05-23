"""Authentication and broker-credential management endpoints.

POST /api/auth/login                        — authenticate dashboard user, derive session key
GET  /api/auth/status                       — auth status (authenticated, bot locked/unlocked)
GET  /api/auth/profiles                     — list all profiles for the authenticated user
POST /api/auth/profiles                     — create a new encrypted broker profile
POST /api/auth/profiles/{id}/activate      — set active profile and unlock the bot
POST /api/auth/profiles/{id}/delete         — delete a profile
POST /api/auth/unlock                       — called by dashboard to push derived key to bot
POST /api/auth/switch-profile               — switch profile with re-derived key
"""

from __future__ import annotations

import base64
import logging
import secrets
import time

import bcrypt
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from adapters.db.credentials import BrokerCredentials, CredentialStore, ProfileSummary
from adapters.db.db import Database
from orchestrator.bot_singleton import get_bot

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory session store ─────────────────────────────────────────────────
# session_token -> {"user_id", "username", "expires_at", "derived_key_b64"}
_sessions: dict[str, dict] = {}


def _create_session(user_id: int, username: str, derived_key_b64: str) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + 86400
    _sessions[token] = {
        "user_id": user_id,
        "username": username,
        "expires_at": expires_at,
        "derived_key_b64": derived_key_b64,
    }
    return token, expires_at


def _validate_session(token: str) -> dict | None:
    sess = _sessions.get(token)
    if not sess:
        return None
    if time.time() > sess["expires_at"]:
        del _sessions[token]
        return None
    return sess


# ── Lazy DB singletons ────────────────────────────────────────────────────────

_db: Database | None = None
_cred_store: CredentialStore | None = None


def _get_db() -> Database:
    global _db
    if _db is None:
        from config import settings as s
        _db = Database(dsn=s.DATABASE_URL)
    return _db


def _get_cred_store() -> CredentialStore:
    global _cred_store
    if _cred_store is None:
        _cred_store = CredentialStore(_get_db()._pool)  # noqa: SLF001
    return _cred_store


# ── Request / response models ───────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user_id: int
    username: str
    session_token: str
    expires_at: int


class ProfileCreateRequest(BaseModel):
    profile_label: str = Field(..., min_length=1, max_length=50)
    account_number: str = Field(..., min_length=1)
    server: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class ProfileResponse(BaseModel):
    id: int
    profile_label: str
    account_number: str
    server: str
    is_demo: bool
    is_active: bool


class UnlockRequest(BaseModel):
    session_token: str
    profile_id: int
    derived_key: str  # base64-encoded 32-byte key


class UnlockResponse(BaseModel):
    ok: bool
    account: str
    server: str


class SwitchProfileRequest(BaseModel):
    session_token: str
    profile_id: int
    dashboard_password: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user_id: int | None
    username: str | None
    bot_locked: bool
    active_profile_id: int | None


# ── Auth helper ───────────────────────────────────────────────────────────────

def _require_auth(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth.removeprefix("Bearer ").strip()
    sess = _validate_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return sess


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate a dashboard user with username + bcrypt password hash."""
    db = _get_db()
    user = db.users.get_user_by_username(body.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        if not bcrypt.checkpw(body.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as exc:
        logger.warning("Bcrypt verify failed for %s: %s", body.username, exc)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Stable per-user salt stored in bot_memory
    salt_b64 = db.read_memory_block(f"user_salt:{user['id']}")
    if not salt_b64:
        salt_bytes = secrets.token_bytes(16)
        salt_b64 = base64.b64encode(salt_bytes).decode()
        db.write_memory_block(f"user_salt:{user['id']}", salt_b64)

    salt_bytes = base64.b64decode(salt_b64)
    key_bytes = CredentialStore.derive_key.__func__(None, body.password, salt_bytes)
    derived_key_b64 = base64.b64encode(key_bytes).decode()

    token, expires_at = _create_session(user["id"], user["username"], derived_key_b64)
    logger.info("User %s logged in successfully", body.username)
    return LoginResponse(
        user_id=user["id"],
        username=user["username"],
        session_token=token,
        expires_at=expires_at,
    )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(request: Request) -> AuthStatusResponse:
    try:
        sess = _require_auth(request)
    except HTTPException:
        return AuthStatusResponse(
            authenticated=False, user_id=None, username=None,
            bot_locked=True, active_profile_id=None,
        )

    profiles = _get_cred_store().list_profiles(user_id=sess["user_id"])
    active = next((p for p in profiles if p.is_active), None)

    return AuthStatusResponse(
        authenticated=True,
        user_id=sess["user_id"],
        username=sess["username"],
        bot_locked=active is None,
        active_profile_id=active.id if active else None,
    )


@router.get("/profiles")
async def list_profiles(request: Request) -> list[ProfileResponse]:
    sess = _require_auth(request)
    profiles = _get_cred_store().list_profiles(user_id=sess["user_id"])
    return [
        ProfileResponse(
            id=p.id,
            profile_label=p.profile_label,
            account_number=p.account_number,
            server=p.server,
            is_demo=False,
            is_active=p.is_active,
        )
        for p in profiles
    ]


@router.post("/profiles", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(body: ProfileCreateRequest, request: Request) -> ProfileResponse:
    sess = _require_auth(request)
    derived_key = base64.b64decode(sess["derived_key_b64"])

    profile_id = _get_cred_store().store(
        user_id=sess["user_id"],
        profile_label=body.profile_label,
        account_number=body.account_number,
        server=body.server,
        password=body.password,
        derived_key=derived_key,
    )
    _get_cred_store().set_active(profile_id, user_id=sess["user_id"])
    logger.info("Profile created id=%d for user %s", profile_id, sess["username"])

    return ProfileResponse(
        id=profile_id,
        profile_label=body.profile_label,
        account_number=body.account_number,
        server=body.server,
        is_demo=False,
        is_active=True,
    )


@router.post("/profiles/{profile_id}/activate")
async def activate_profile(profile_id: int, request: Request) -> dict:
    sess = _require_auth(request)
    profiles = _get_cred_store().list_profiles(user_id=sess["user_id"])
    if not any(p.id == profile_id for p in profiles):
        raise HTTPException(status_code=404, detail="Profile not found")
    _get_cred_store().set_active(profile_id, user_id=sess["user_id"])
    logger.info("Profile %d activated for user %s", profile_id, sess["username"])
    return {"ok": True}


@router.post("/profiles/{profile_id}/delete")
async def delete_profile(profile_id: int, request: Request) -> dict:
    sess = _require_auth(request)
    profiles = _get_cred_store().list_profiles(user_id=sess["user_id"])
    if not any(p.id == profile_id for p in profiles):
        raise HTTPException(status_code=404, detail="Profile not found")
    _get_cred_store().delete(profile_id, user_id=sess["user_id"])
    logger.info("Profile %d deleted for user %s", profile_id, sess["username"])
    return {"ok": True}


@router.post("/unlock", response_model=UnlockResponse)
async def unlock(body: UnlockRequest) -> UnlockResponse:
    """Called by the dashboard after login to unlock the trading bot.

    Decrypts the stored MT5 credentials and establishes the MT5 connection.
    The bot transitions from WAITING_FOR_AUTH → RUNNING.
    """
    sess = _validate_session(body.session_token)
    if not sess:
        raise HTTPException(status_code=401, detail="Session expired")

    if sess["derived_key_b64"] != body.derived_key:
        raise HTTPException(status_code=401, detail="Key mismatch — re-login required")

    derived_key = base64.b64decode(body.derived_key)

    try:
        creds: BrokerCredentials = _get_cred_store().load(
            profile_id=body.profile_id,
            derived_key=derived_key,
            user_id=sess["user_id"],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.warning("Decrypt failed profile %d: %s", body.profile_id, exc)
        raise HTTPException(status_code=401, detail="Decryption failed — wrong key or corrupted data")

    # ── Wire into the running TradingBot ────────────────────────────────
    bot = get_bot()
    if not bot:
        raise HTTPException(status_code=503, detail="Bot not running")

    try:
        bot.unlock_with_credentials(
            account_id=body.profile_id,
            account_number=creds.account,
            password=creds.password,
            server=creds.server,
        )
    except Exception as exc:
        logger.warning("Bot unlock failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    _get_cred_store().update_last_connected(body.profile_id)
    logger.info("Bot unlocked for user %s, profile %d", sess["username"], body.profile_id)
    return UnlockResponse(ok=True, account=creds.account, server=creds.server)


@router.post("/switch-profile", response_model=UnlockResponse)
async def switch_profile(body: SwitchProfileRequest) -> UnlockResponse:
    sess = _validate_session(body.session_token)
    if not sess:
        raise HTTPException(status_code=401, detail="Session expired")

    db = _get_db()
    salt_b64 = db.read_memory_block(f"user_salt:{sess['user_id']}")
    if not salt_b64:
        raise HTTPException(status_code=400, detail="No salt found — re-login required")

    salt_bytes = base64.b64decode(salt_b64)
    key_bytes = CredentialStore.derive_key.__func__(None, body.dashboard_password, salt_bytes)
    derived_key = base64.b64decode(base64.b64encode(key_bytes).decode())

    try:
        creds: BrokerCredentials = _get_cred_store().load(
            profile_id=body.profile_id,
            derived_key=derived_key,
            user_id=sess["user_id"],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.warning("Profile switch decrypt failed for %d: %s", body.profile_id, exc)
        raise HTTPException(status_code=401, detail="Decryption failed — wrong password")

    _get_cred_store().set_active(body.profile_id, user_id=sess["user_id"])

    # ── Wire into the running TradingBot ────────────────────────────────
    bot = get_bot()
    if bot:
        try:
            bot.switch_profile(
                account_id=body.profile_id,
                account_number=creds.account,
                password=creds.password,
                server=creds.server,
            )
        except Exception as exc:
            logger.warning("Profile switch failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    _get_cred_store().update_last_connected(body.profile_id)
    logger.info("Profile switched to %d for user %s", body.profile_id, sess["username"])
    return UnlockResponse(ok=True, account=creds.account, server=creds.server)