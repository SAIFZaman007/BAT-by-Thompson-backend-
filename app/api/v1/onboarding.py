import secrets

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.entities import OnboardingSubmission
from app.schemas.api import OnboardingIn, OnboardingOut
from app.services.email import send_confirmation

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("", response_model=OnboardingOut, status_code=201)
@limiter.limit("5/minute")
def create_submission(request: Request, payload: OnboardingIn, db: Session = Depends(get_db)):
    ref = secrets.token_hex(4).upper()  # 8-char human-friendly reference
    sub = OnboardingSubmission(reference_code=ref, **payload.model_dump())
    db.add(sub)
    db.commit()
    send_confirmation(payload.email, ref)
    return OnboardingOut(
        reference_code=ref,
        message="Application received. Keep this reference code — you'll use it to upload your KYC documents.",
    )
