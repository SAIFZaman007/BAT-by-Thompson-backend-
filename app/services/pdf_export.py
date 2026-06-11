"""PDF export builders for the admin dashboard.

Two kinds of export are produced:

1. Per-user "case file" PDF — onboarding info, KYC document list, and every
   support/contact message sent using that user's email address.
2. All-users bulk PDF — one section per submission, same shape as (1), for
   when the admin wants a single consolidated archive instead of clicking
   through each user individually.

Generation is done in-memory with reportlab and returned as raw bytes so the
API layer can stream it straight back as a download — nothing is written to
disk.
"""
from __future__ import annotations

import datetime as dt
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.entities import ContactMessage, KycDocument, OnboardingSubmission

_STYLES = getSampleStyleSheet()
_TITLE = ParagraphStyle(
    "BatTitle", parent=_STYLES["Title"], textColor=colors.HexColor("#0B1B33"), spaceAfter=4
)
_SUBTITLE = ParagraphStyle(
    "BatSubtitle", parent=_STYLES["Normal"], textColor=colors.HexColor("#64748B"), fontSize=9
)
_SECTION = ParagraphStyle(
    "BatSection",
    parent=_STYLES["Heading2"],
    textColor=colors.HexColor("#173EA5"),
    spaceBefore=14,
    spaceAfter=6,
)
_LABEL = ParagraphStyle("BatLabel", parent=_STYLES["Normal"], textColor=colors.HexColor("#64748B"), fontSize=8)
_BODY = ParagraphStyle("BatBody", parent=_STYLES["Normal"], fontSize=10, leading=14)
_SMALL = ParagraphStyle("BatSmall", parent=_STYLES["Normal"], fontSize=8.5, textColor=colors.HexColor("#475569"))


def _fmt_dt(value: dt.datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d %b %Y, %H:%M UTC")


def _info_table(sub: OnboardingSubmission) -> Table:
    rows = [
        ["Reference code", sub.reference_code],
        ["Full name", sub.full_name],
        ["Email", sub.email],
        ["Phone", sub.phone],
        ["Wallet address", sub.wallet_address],
        ["Status", sub.status.value if hasattr(sub.status, "value") else str(sub.status)],
        ["Submitted", _fmt_dt(sub.created_at)],
    ]
    if sub.details:
        rows.append(["Details", sub.details])

    table_data = [
        [Paragraph(f"<b>{label}</b>", _SMALL), Paragraph(str(value), _BODY)] for label, value in rows
    ]
    table = Table(table_data, colWidths=[40 * mm, 130 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E2E8F0")),
            ]
        )
    )
    return table


def _kyc_table(documents: list[KycDocument]) -> Table | Paragraph:
    if not documents:
        return Paragraph("No KYC documents uploaded yet.", _SMALL)

    header = [Paragraph("<b>File name</b>", _SMALL), Paragraph("<b>Type</b>", _SMALL), Paragraph("<b>Uploaded</b>", _SMALL)]
    rows = [header]
    for doc in documents:
        rows.append(
            [
                Paragraph(doc.original_name, _BODY),
                Paragraph(doc.mime_type, _SMALL),
                Paragraph(_fmt_dt(doc.created_at), _SMALL),
            ]
        )
    table = Table(rows, colWidths=[90 * mm, 40 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0FB")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#173EA5")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _messages_table(messages: list[ContactMessage]) -> Table | Paragraph:
    if not messages:
        return Paragraph("No support messages from this user yet.", _SMALL)

    header = [Paragraph("<b>Date</b>", _SMALL), Paragraph("<b>Message</b>", _SMALL)]
    rows = [header]
    for msg in messages:
        rows.append(
            [
                Paragraph(_fmt_dt(msg.created_at), _SMALL),
                Paragraph(msg.message.replace("\n", "<br/>"), _BODY),
            ]
        )
    table = Table(rows, colWidths=[35 * mm, 135 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E3F4F2")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#0E9E8F")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _user_section(sub: OnboardingSubmission, messages: list[ContactMessage]) -> list:
    flow: list = []
    flow.append(Paragraph(sub.full_name, _TITLE))
    flow.append(
        Paragraph(
            f"Reference {sub.reference_code} &nbsp;·&nbsp; Generated {_fmt_dt(dt.datetime.utcnow())}",
            _SUBTITLE,
        )
    )
    flow.append(Spacer(1, 8))
    flow.append(HRFlowable(width="100%", color=colors.HexColor("#E2E8F0"), thickness=1))

    flow.append(Paragraph("Onboarding information", _SECTION))
    flow.append(_info_table(sub))

    flow.append(Paragraph("KYC documents", _SECTION))
    flow.append(_kyc_table(sub.kyc_documents))

    flow.append(Paragraph("Support messages", _SECTION))
    flow.append(_messages_table(messages))

    return flow


def build_user_pdf(sub: OnboardingSubmission, messages: list[ContactMessage]) -> bytes:
    """Single-user case-file PDF: onboarding info + KYC list + support emails."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"{sub.full_name} — {sub.reference_code}",
    )
    doc.build(_user_section(sub, messages))
    return buffer.getvalue()


def build_all_users_pdf(rows: list[tuple[OnboardingSubmission, list[ContactMessage]]]) -> bytes:
    """Combined PDF archive: one section per submission, page break between."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title="All user submissions export",
    )

    flow: list = [
        Paragraph("Bahamas AI Trading — All Submissions Export", _TITLE),
        Paragraph(f"Generated {_fmt_dt(dt.datetime.utcnow())} &nbsp;·&nbsp; {len(rows)} user(s)", _SUBTITLE),
        Spacer(1, 10),
    ]
    for index, (sub, messages) in enumerate(rows):
        if index > 0:
            flow.append(PageBreak())
        flow.extend(_user_section(sub, messages))

    doc.build(flow)
    return buffer.getvalue()
