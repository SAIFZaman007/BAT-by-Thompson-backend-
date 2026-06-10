from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.entities import ContactMessage
from app.schemas.api import ContactIn

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", status_code=201)
@limiter.limit("5/minute")
def create_message(request: Request, payload: ContactIn, db: Session = Depends(get_db)):
    db.add(ContactMessage(**payload.model_dump()))
    db.commit()
    return {"message": "Message sent. Support replies by email, usually within one business day."}
