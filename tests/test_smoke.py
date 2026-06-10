"""Run with: pytest (uses SQLite in-memory via env override if you wire it; smoke-level only)."""
from app.schemas.api import OnboardingIn


def test_onboarding_schema_strips_whitespace():
    o = OnboardingIn(
        full_name="  Jane Doe ", email="jane@example.com",
        phone="+1 242 555 0100", wallet_address="T" * 30, details=" hi ",
    )
    assert o.full_name == "Jane Doe"
    assert o.details == "hi"