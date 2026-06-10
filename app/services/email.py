"""Submission confirmation email. Stubbed: logs in development, plug SMTP/Resend in prod.

Deliberately minimal so the client can choose a provider. Swap `send` body
for smtplib or an HTTP API call; the call sites won't change.
"""
import logging

logger = logging.getLogger("bat.email")


def send_confirmation(to: str, reference_code: str) -> None:
    logger.info("confirmation queued: to=%s ref=%s", to, reference_code)