"""Auth, password hashing, JWT, and KYC file validation/encryption.

MIME detection uses pure-Python magic-byte inspection instead of python-magic /
libmagic. This removes the native DLL dependency that crashes on Windows and
requires libmagic.so on Linux. The three allowed types (PDF, JPEG, PNG) have
unambiguous leading byte signatures that need no C library to identify.
"""
from __future__ import annotations

import datetime as dt
import uuid

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ALGORITHM = "HS256"

_EXT_FOR_MIME = {
    "application/pdf": ".pdf",
    "image/jpeg":      ".jpg",
    "image/png":       ".png",
}


# ── Pure-Python MIME detection ────────────────────────────────────────────────

def _detect_mime(data: bytes) -> str | None:
    """
    Identify file type from leading magic bytes — no native libraries needed.

    Signatures:
        PDF   %PDF          (25 50 44 46)
        JPEG  FF D8 FF      (all JPEG variants: JFIF, EXIF, raw, progressive)
        PNG   89 50 4E 47 0D 0A 1A 0A  (full 8-byte PNG signature)

    Returns the MIME string, or None if the data doesn't match any allowed type.
    A file shorter than 4 bytes always returns None (can't be a valid document).
    """
    if len(data) < 4:
        return None
    if data[:4] == b"%PDF":
        return "application/pdf"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return None


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(subject: str) -> str:
    s = get_settings()
    expire = (
        dt.datetime.now(dt.timezone.utc)
        + dt.timedelta(minutes=s.access_token_expire_minutes)
    )
    return jwt.encode({"sub": subject, "exp": expire}, s.secret_key, algorithm=ALGORITHM)


def decode_token(token: str = Depends(oauth2_scheme)) -> str:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.secret_key, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Session expired or invalid. Sign in again.",
        )


# ── KYC upload validation ─────────────────────────────────────────────────────

async def validate_kyc_upload(file: UploadFile) -> tuple[bytes, str]:
    """Read, size-check and magic-byte-validate an upload.

    Returns (raw_bytes, safe_extension).  Raises 400 / 413 on violation.
    The file extension is derived from the *detected* MIME type — never from
    the client-supplied filename, which cannot be trusted.
    """
    s = get_settings()

    data = await file.read()

    if len(data) == 0:
        raise HTTPException(400, "The file is empty. Choose a PDF, JPG or PNG and try again.")

    if len(data) > s.max_upload_bytes:
        raise HTTPException(413, "File is larger than 10 MB. Compress it or upload a smaller scan.")

    detected = _detect_mime(data)
    if detected is None or detected not in s.allowed_mime_types:
        raise HTTPException(400, "Unsupported file type. Upload a PDF, JPG or PNG.")

    return data, _EXT_FOR_MIME[detected]


# ── Fernet encryption helpers ─────────────────────────────────────────────────

def get_fernet() -> Fernet:
    s = get_settings()
    if not s.fernet_key:
        raise RuntimeError(
            "FERNET_KEY is not configured — refusing to store KYC files unencrypted."
        )
    return Fernet(s.fernet_key.encode())


def random_filename(ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}.enc"