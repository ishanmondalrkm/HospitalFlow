"""Authentication primitives for HospitalFlow Phase 9A.

Phase 9A establishes account authentication and signed bearer tokens. Role
permissions are intentionally kept for Phase 9B; this module only answers
"who is this user?" and never decides what they may do.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pymongo.errors import PyMongoError

from backend import config as cfg
from backend.db import mongo

ALGORITHM = "HS256"
COLLECTION = "users"
TOKEN_EXPIRE_MINUTES = max(5, int(os.getenv("HOSPITALFLOW_AUTH_TOKEN_MINUTES", "480")))
AUTH_SECRET = os.getenv("HOSPITALFLOW_AUTH_SECRET", "")
DEMO_SEED = os.getenv("HOSPITALFLOW_AUTH_SEED_DEMO", "true").lower() in {"1", "true", "yes", "on"}


def _secret() -> str:
    if AUTH_SECRET:
        return AUTH_SECRET
    # A development fallback keeps the hackathon build easy to run. Production
    # deployment must set HOSPITALFLOW_AUTH_SECRET to a long random value.
    return f"hospitalflow-dev-secret::{cfg.MONGODB_DATABASE}"


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)
    return f"pbkdf2_sha256$240000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def ensure_indexes() -> None:
    if not mongo.is_available():
        return
    try:
        mongo.database()[COLLECTION].create_index("username", unique=True)
    except PyMongoError:
        pass


def ensure_demo_users() -> None:
    if not DEMO_SEED or not mongo.is_available():
        return
    users = mongo.database()[COLLECTION]
    demo_users = (
        ("admin", "admin123", "Administrator"),
        ("manager", "manager123", "Operations Manager"),
        ("viewer", "viewer123", "Staff / Viewer"),
    )
    for username, password, role in demo_users:
        if users.find_one({"username": username}, {"_id": 1}):
            continue
        users.insert_one({
            "username": username,
            "password_hash": hash_password(password),
            "role": role,
            "active": True,
            "created_at": datetime.now(timezone.utc),
        })


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    if not mongo.is_available():
        return None
    user = mongo.database()[COLLECTION].find_one({"username": username.strip().lower(), "active": True})
    if not user or not verify_password(password, user.get("password_hash", "")):
        return None
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "role": user.get("role", "Staff / Viewer"),
    }


def create_access_token(user: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": expires,
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
