from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import validate_kyc_upload
from app.db.session import get_db
from app.models.entities import KycDocument, OnboardingSubmission
from app.schemas.api import KycUploadOut
from app.services.storage import save_encrypted

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.post("/upload", response_model=KycUploadOut, status_code=201)
@limiter.limit("10/hour")
async def upload_kyc(
    request: Request,
    reference_code: str = Form(min_length=6, max_length=12),
    file: UploadFile = None,
    db: Session = Depends(get_db),
):
    if file is None:
        raise HTTPException(400, "Attach a PDF, JPG or PNG of your ID document.")
    sub = db.scalar(
        select(OnboardingSubmission).where(
            OnboardingSubmission.reference_code == reference_code.strip().upper()
        )
    )
    if sub is None:
        raise HTTPException(404, "Reference code not found. Check the code from your onboarding confirmation.")
    data, ext = await validate_kyc_upload(file)
    stored = save_encrypted(data, ext)
    doc = KycDocument(
        submission_id=sub.id,
        stored_name=stored,
        original_name=(file.filename or "document")[:255],
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(doc)
    db.commit()
    return KycUploadOut(document_id=doc.id, message="Document received securely. Our team will review it.")
