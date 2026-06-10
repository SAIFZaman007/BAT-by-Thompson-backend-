from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.entities import AdminUser
from app.schemas.api import TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(AdminUser).where(AdminUser.username == form.username))
    if user is None or not verify_password(form.password, user.password_hash):
        # identical error either way — no username enumeration
        raise HTTPException(401, "Incorrect username or password.")
    return TokenOut(access_token=create_access_token(user.username))
