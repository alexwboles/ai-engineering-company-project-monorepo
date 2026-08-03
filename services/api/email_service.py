from __future__ import annotations

import os

import resend


def _resend_api_key() -> str:
    return os.getenv("RESEND_API_KEY", "").strip()


def _resend_from_email() -> str:
    return os.getenv("RESEND_FROM_EMAIL", "").strip()


def _frontend_reset_password_url() -> str:
    return os.getenv("FRONTEND_RESET_PASSWORD_URL", "http://localhost:3000/reset-password").strip()


def build_reset_password_link(token: str) -> str:
    base_url = _frontend_reset_password_url()
    joiner = "&" if "?" in base_url else "?"
    return f"{base_url}{joiner}token={token}"


def send_password_reset_email(*, recipient_email: str, reset_token: str) -> bool:
    api_key = _resend_api_key()
    from_email = _resend_from_email()
    if not api_key or not from_email:
        # Keep auth flow safe in local/dev when email is not configured.
        return False

    reset_link = build_reset_password_link(reset_token)
    subject = "HealthCore password reset"
    text_body = (
        "We received a request to reset your HealthCore password. "
        "Use the link below to choose a new password:\n\n"
        f"{reset_link}\n\n"
        "This link expires shortly and can only be used once."
    )

    html_body = (
        "<div style='font-family:Arial,sans-serif;line-height:1.5;color:#0f172a;'>"
        "<h2 style='margin:0 0 12px;'>Reset your HealthCore password</h2>"
        "<p style='margin:0 0 12px;'>"
        "We received a request to reset your password. "
        "Tap the button below to set a new password."
        "</p>"
        f"<p style='margin:16px 0;'><a href='{reset_link}' "
        "style='display:inline-block;background:#0f766e;color:#ffffff;padding:10px 16px;"
        "text-decoration:none;border-radius:6px;font-weight:600;'>Reset password</a></p>"
        f"<p style='margin:0 0 12px;word-break:break-all;'>If the button does not work, use this link: {reset_link}</p>"
        "<p style='margin:0;color:#475569;'>This link expires shortly and can only be used once.</p>"
        "</div>"
    )

    try:
        resend.api_key = api_key
        resend.Emails.send(
            {
                "from": from_email,
                "to": [recipient_email],
                "subject": subject,
                "text": text_body,
                "html": html_body,
            }
        )
        return True
    except Exception:
        return False
