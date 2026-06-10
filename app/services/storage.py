"""Encrypted-at-rest private file storage for KYC documents.

Files live under settings.upload_dir, OUTSIDE any statically-served path,
with random names and Fernet encryption. The only read path is the
authenticated admin endpoint, which also writes an audit log entry.
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.security import get_fernet, random_filename


def save_encrypted(data: bytes, ext: str) -> str:
    s = get_settings()
    root = Path(s.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    name = random_filename(ext)
    (root / name).write_bytes(get_fernet().encrypt(data))
    return name


def read_decrypted(stored_name: str) -> bytes:
    # stored_name only ever comes from our own DB, but defend in depth anyway:
    if "/" in stored_name or "\\" in stored_name or ".." in stored_name:
        raise ValueError("Invalid stored file name.")
    path = Path(get_settings().upload_dir) / stored_name
    return get_fernet().decrypt(path.read_bytes())