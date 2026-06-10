"""
Unified seed script — demo data + admin creation in one place.

─────────────────────────────────────────────────────────────────────────────
HOW TO RUN  (both forms work — see explanation below)
─────────────────────────────────────────────────────────────────────────────

  # Recommended — run as a module (from backend/ directory):
  python -m scripts.seed                    # seed demo data
  python -m scripts.seed --admin yourname   # create/reset one admin
  python -m scripts.seed --all              # demo data + admin prompt
  python -m scripts.seed --reset            # wipe rows, re-seed

  # Also works — run as a plain script (VS Code Run button, etc.):
  python scripts/seed.py
  python scripts/seed.py --admin yourname

─────────────────────────────────────────────────────────────────────────────
WHY "No module named 'app'" HAPPENS
─────────────────────────────────────────────────────────────────────────────

When Python runs a file directly (`python scripts/seed.py`), it adds the
FILE'S directory (backend/scripts/) to sys.path[0], not the project root.
So `import app` fails because `app/` lives in backend/, not backend/scripts/.

When Python runs a module (`python -m scripts.seed`), it adds the CURRENT
WORKING DIRECTORY (backend/) to sys.path[0], so `import app` resolves to
backend/app/ — exactly right.

The __file__-based sys.path.insert below makes the direct-run form safe too.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import argparse
import getpass
import os
import random
import secrets
import sys
from pathlib import Path

# ── Path fix ─────────────────────────────────────────────────────────────────
# Insert the backend/ directory at the front of sys.path so that
# `import app` works regardless of HOW this script is invoked:
#   • python scripts/seed.py          (sys.path[0] = backend/scripts)  ← fixed
#   • python -m scripts.seed          (sys.path[0] = backend)          ← already ok
#   • VS Code "Run Python File" button                                  ← fixed
_BACKEND_DIR = Path(__file__).resolve().parent.parent   # …/backend/scripts/../ = …/backend/
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ── Also load the .env from backend/ so Settings() picks it up ───────────────
os.chdir(_BACKEND_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Demo fixtures
# ─────────────────────────────────────────────────────────────────────────────

# A tiny valid one-page PDF so admin "View document" actually renders something.
_MINI_PDF = (
    b"%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

_PEOPLE = [
    ("Amara Rolle",    "amara.rolle@example.com"),
    ("Devon Ferguson", "devon.f@example.com"),
    ("Keisha Moss",    "keisha.moss@example.com"),
    ("Marcus Bethel",  "m.bethel@example.com"),
    ("Tanya Albury",   "tanya.albury@example.com"),
    ("Leon Strachan",  "leon.s@example.com"),
    ("Bria Knowles",   "bria.knowles@example.com"),
    ("Omar Saunders",  "omar.saunders@example.com"),
]

_MESSAGES = [
    ("Patrice Curry", "patrice@example.com",
     "Hi, I submitted my application yesterday — how long does KYC review usually take?"),
    ("Jerome Pinder",  "jerome.p@example.com",
     "Can I update the wallet address I entered on my onboarding form?"),
    ("Selena Dean",    "selena.dean@example.com",
     "Please confirm you received my withdrawal notice sent last week."),
]


# ─────────────────────────────────────────────────────────────────────────────
# Lazy imports — only after path is fixed
# ─────────────────────────────────────────────────────────────────────────────

def _import_deps():
    """Import app modules after sys.path is already correct."""
    try:
        from sqlalchemy import select, delete          # noqa: PLC0415
        from app.core.security import hash_password    # noqa: PLC0415
        from app.db.session import Base, SessionLocal, engine  # noqa: PLC0415
        from app.models.entities import (              # noqa: PLC0415
            AdminUser, ContactMessage, KycDocument,
            OnboardingSubmission, SubmissionStatus,
        )
        from app.services.storage import save_encrypted  # noqa: PLC0415
    except ImportError as exc:
        sys.exit(
            f"\n❌  Import error: {exc}\n\n"
            "Checklist:\n"
            "  1. Activate the venv first:\n"
            "       source venv/Scripts/activate    (Windows / Git Bash)\n"
            "       source venv/bin/activate        (Linux / Mac)\n"
            "  2. Install dependencies:\n"
            "       pip install -r requirements.txt\n"
            "       pip install python-magic-bin    (Windows only)\n"
            "  3. You must be inside the backend/ directory:\n"
            "       cd bahamas-ai-trading/backend\n"
        )
    return (
        select, delete,
        hash_password,
        Base, SessionLocal, engine,
        AdminUser, ContactMessage, KycDocument,
        OnboardingSubmission, SubmissionStatus,
        save_encrypted,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Actions
# ─────────────────────────────────────────────────────────────────────────────

def _create_or_reset_admin(db, AdminUser, hash_password, select,
                            username: str | None = None) -> None:
    if username is None:
        username = input("Admin username: ").strip()
    if not username:
        print("⚠️  No username entered — skipped.")
        return

    password = getpass.getpass(f"Password for '{username}': ")
    if len(password) < 12:
        sys.exit("❌  Password must be at least 12 characters.")

    user = db.scalar(select(AdminUser).where(AdminUser.username == username))
    if user:
        user.password_hash = hash_password(password)
        print(f"✅  Password reset for admin '{username}'.")
    else:
        db.add(AdminUser(username=username, password_hash=hash_password(password)))
        print(f"✅  Admin '{username}' created.")
    db.commit()


def _seed_demo(db, select, delete, AdminUser, ContactMessage, KycDocument,
               OnboardingSubmission, SubmissionStatus, save_encrypted,
               hash_password, reset: bool = False) -> None:

    if reset:
        db.execute(delete(KycDocument))
        db.execute(delete(ContactMessage))
        db.execute(delete(OnboardingSubmission))
        db.commit()
        print("🗑️  Existing demo rows cleared.")

    elif db.scalar(select(OnboardingSubmission).limit(1)):
        print("ℹ️  Demo data already present. Use --reset to wipe and re-seed.")
        return

    # Demo admin (only if none exists yet)
    if not db.scalar(select(AdminUser).where(AdminUser.username == "admin")):
        db.add(AdminUser(username="admin",
                         password_hash=hash_password("AdminPass123!")))
        print("👤  Demo admin →  username: admin  /  password: AdminPass123!")
        print("    ⚠️  Change this immediately in any non-local environment.")

    statuses = list(SubmissionStatus)
    for i, (name, email) in enumerate(_PEOPLE):
        sub = OnboardingSubmission(
            reference_code=secrets.token_hex(4).upper(),
            full_name=name,
            email=email,
            phone=f"+1 242 555 0{100 + i}",
            wallet_address="T" + secrets.token_hex(16).upper(),
            details=random.choice(
                ["", "Referred by a current client.", "Prefers contact by email."]
            ),
            status=statuses[i % len(statuses)],
        )
        db.add(sub)
        db.flush()

        if i % 3 != 0:          # ~2/3 of applicants have a KYC doc
            stored = save_encrypted(_MINI_PDF, ".pdf")
            db.add(KycDocument(
                submission_id=sub.id,
                stored_name=stored,
                original_name=f"{name.split()[0].lower()}_passport.pdf",
                mime_type="application/pdf",
            ))

    for n, e, m in _MESSAGES:
        db.add(ContactMessage(name=n, email=e, message=m))

    db.commit()
    print(f"🌱  Seeded {len(_PEOPLE)} submissions + {len(_MESSAGES)} contact messages.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Seed the Bahamas AI Trading database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python -m scripts.seed                   # seed demo data\n"
            "  python -m scripts.seed --admin alice     # create/reset admin\n"
            "  python -m scripts.seed --all             # demo data + admin\n"
            "  python -m scripts.seed --reset           # wipe + re-seed\n"
            "\n"
            "  python scripts/seed.py                   # also works!\n"
        ),
    )
    p.add_argument("--admin", metavar="USERNAME",
                   help="Create or reset password for this admin username.")
    p.add_argument("--all", action="store_true",
                   help="Seed demo data AND prompt to create an admin account.")
    p.add_argument("--reset", action="store_true",
                   help="Wipe all data rows, then re-seed.")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    (
        select, delete,
        hash_password,
        Base, SessionLocal, engine,
        AdminUser, ContactMessage, KycDocument,
        OnboardingSubmission, SubmissionStatus,
        save_encrypted,
    ) = _import_deps()

    Base.metadata.create_all(bind=engine)   # safe to re-run; no-ops if tables exist

    with SessionLocal() as db:

        if args.admin:
            _create_or_reset_admin(db, AdminUser, hash_password, select,
                                   username=args.admin)

        elif args.all:
            _seed_demo(db, select, delete, AdminUser, ContactMessage, KycDocument,
                       OnboardingSubmission, SubmissionStatus, save_encrypted,
                       hash_password, reset=args.reset)
            print()
            _create_or_reset_admin(db, AdminUser, hash_password, select)

        else:
            # Default: seed demo data (idempotent unless --reset)
            _seed_demo(db, select, delete, AdminUser, ContactMessage, KycDocument,
                       OnboardingSubmission, SubmissionStatus, save_encrypted,
                       hash_password, reset=args.reset)


if __name__ == "__main__":
    main()