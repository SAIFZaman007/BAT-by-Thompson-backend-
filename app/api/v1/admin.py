from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import decode_token
from app.db.session import get_db
from app.models.entities import (
    AuditLog,
    ContactMessage,
    KycDocument,
    OnboardingSubmission,
    SubmissionStatus,
)
from app.schemas.api import ContactOut, StatusUpdateIn, SubmissionOut
from app.services.storage import read_decrypted

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(decode_token)])


def _audit(db: Session, actor: str, action: str, target: str) -> None:
    db.add(AuditLog(actor=actor, action=action, target=target))
    db.commit()


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    by_status = dict(
        db.execute(
            select(OnboardingSubmission.status, func.count()).group_by(OnboardingSubmission.status)
        ).all()
    )
    return {
        "submissions_total": db.scalar(select(func.count()).select_from(OnboardingSubmission)) or 0,
        "submissions_by_status": {s.value: by_status.get(s, 0) for s in SubmissionStatus},
        "kyc_documents_total": db.scalar(select(func.count()).select_from(KycDocument)) or 0,
        "contact_messages_total": db.scalar(select(func.count()).select_from(ContactMessage)) or 0,
        "awaiting_kyc": db.scalar(
            select(func.count())
            .select_from(OnboardingSubmission)
            .where(
                OnboardingSubmission.status == SubmissionStatus.pending,
                ~OnboardingSubmission.kyc_documents.any(),
            )
        )
        or 0,
    }


@router.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=120, description="search name / email / reference"),
    status: str | None = Query(default=None, pattern="^(pending|reviewed|approved|rejected)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    stmt = (
        select(OnboardingSubmission)
        .options(selectinload(OnboardingSubmission.kyc_documents))
        .order_by(OnboardingSubmission.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                OnboardingSubmission.full_name.ilike(like),
                OnboardingSubmission.email.ilike(like),
                OnboardingSubmission.reference_code.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(OnboardingSubmission.status == status)
    return db.scalars(stmt).all()


@router.patch("/submissions/{submission_id}/status", response_model=SubmissionOut)
def update_status(
    submission_id: str,
    payload: StatusUpdateIn,
    db: Session = Depends(get_db),
    actor: str = Depends(decode_token),
):
    sub = db.get(OnboardingSubmission, submission_id)
    if sub is None:
        raise HTTPException(404, "Submission not found.")
    sub.status = payload.status
    db.commit()
    _audit(db, actor, "submission.status", f"{submission_id}:{payload.status}")
    db.refresh(sub)
    return sub


@router.get("/kyc/{document_id}")
def download_kyc(document_id: str, db: Session = Depends(get_db), actor: str = Depends(decode_token)):
    doc = db.get(KycDocument, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found.")
    data = read_decrypted(doc.stored_name)
    _audit(db, actor, "kyc.view", document_id)
    return Response(
        content=data,
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'inline; filename="{doc.original_name}"'},
    )


@router.get("/contact-messages", response_model=list[ContactOut])
def list_contact_messages(db: Session = Depends(get_db)):
    return db.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc())).all()
