from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, EmailStr, Field, field_validator


class OnboardingIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=40)
    wallet_address: str = Field(min_length=10, max_length=120)
    details: str = Field(default="", max_length=2000)

    @field_validator("full_name", "phone", "wallet_address", "details")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


class OnboardingOut(BaseModel):
    reference_code: str
    message: str


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    message: str = Field(min_length=5, max_length=4000)


class KycUploadOut(BaseModel):
    document_id: str
    message: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class KycDocOut(BaseModel):
    id: str
    original_name: str
    mime_type: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class SubmissionOut(BaseModel):
    id: str
    reference_code: str
    full_name: str
    email: EmailStr
    phone: str
    wallet_address: str
    details: str
    status: str
    created_at: dt.datetime
    kyc_documents: list[KycDocOut] = []

    model_config = {"from_attributes": True}


class StatusUpdateIn(BaseModel):
    status: str = Field(pattern="^(pending|reviewed|approved|rejected)$")


class ContactOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    message: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}
