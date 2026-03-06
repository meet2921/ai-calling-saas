"""
app/core/email.py

Production-ready async email sender with full error visibility.
Never silently swallows errors — prints exact failure reason to console.
"""

import logging
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

log = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> None:
    password = settings.SMTP_PASSWORD.replace(" ", "").strip()
    msg = MIMEMultipart("alternative")
    msg["Subject"]  = subject
    msg["From"]     = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"]       = to_email
    msg["Reply-To"] = settings.SMTP_FROM_EMAIL
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    await aiosmtplib.send(
        msg,
        hostname  = settings.SMTP_HOST,
        port      = settings.SMTP_PORT,
        username  = settings.SMTP_USER,
        password  = password,
        use_tls   = settings.SMTP_TLS,
        start_tls = settings.SMTP_STARTTLS,
        timeout   = 30,
    )


async def _safe_send(to_email: str, subject: str, html: str, text: str, kind: str) -> bool:
    """Wraps send_email. Always returns, never raises. Logs exact error."""
    try:
        await send_email(to_email, subject, html, text)
        print(f"[EMAIL] ✅ {kind} sent → {to_email}")
        return True
    except aiosmtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL] ❌ AUTH ERROR — {kind} to {to_email}")
        print(f"[EMAIL]    {e}")
        print("[EMAIL]    → You need a Gmail APP PASSWORD (16 chars, no spaces)")
        print("[EMAIL]    → Go to: https://myaccount.google.com/apppasswords")
    except aiosmtplib.SMTPConnectError as e:
        print(f"[EMAIL] ❌ CONNECT ERROR — {kind} to {to_email}")
        print(f"[EMAIL]    {e}")
        print(f"[EMAIL]    → Port {settings.SMTP_PORT} is blocked by your network/firewall")
    except Exception as e:
        print(f"[EMAIL] ❌ FAILED — {kind} to {to_email}")
        print(f"[EMAIL]    {type(e).__name__}: {e}")
        traceback.print_exc()
    return False


# ─── Welcome Email ────────────────────────────────────────────────────────────

async def send_welcome_email(to_email: str, first_name: str, org_name: str, login_url: str) -> bool:
    subject = f"Welcome to {settings.APP_NAME}!"
    c = "#4f46e5"   # brand colour — change to your brand colour

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:560px;">

  <!-- HEADER -->
  <tr><td style="background:#1a1a2e;padding:32px 40px;">
    <h1 style="margin:0;color:#fff;font-size:24px;font-weight:700;">{settings.APP_NAME}</h1>
  </td></tr>

  <!-- BODY -->
  <tr><td style="padding:40px 40px 32px;">
    <h2 style="margin:0 0 16px;font-size:22px;color:#1a1a2e;">Welcome, {first_name}! &#x1F44B;</h2>
    <p style="margin:0 0 6px;font-size:15px;color:#555;line-height:1.7;">
      Your account has been created successfully.
    </p>
    <p style="margin:0 0 28px;font-size:15px;color:#555;line-height:1.7;">
      Organization: <strong style="color:#1a1a2e;">{org_name}</strong>
    </p>

    <!-- CTA -->
    <table cellpadding="0" cellspacing="0" style="margin:0 0 28px;">
      <tr><td style="border-radius:8px;background:{c};">
        <a href="{login_url}"
           style="display:inline-block;padding:14px 32px;color:#fff;
                  font-size:15px;font-weight:600;text-decoration:none;border-radius:8px;">
          Log in to {settings.APP_NAME} &rarr;
        </a>
      </td></tr>
    </table>

    <p style="margin:0;font-size:13px;color:#999;">
      Or copy: <a href="{login_url}" style="color:{c};word-break:break-all;">{login_url}</a>
    </p>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="padding:20px 40px;border-top:1px solid #f0f0f0;">
    <p style="margin:0;font-size:12px;color:#aaa;line-height:1.6;">
      You received this because you registered at {settings.APP_NAME}.
      If this wasn't you, ignore this email.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    text = (
        f"Welcome to {settings.APP_NAME}, {first_name}!\n\n"
        f"Organization: {org_name}\n\n"
        f"Log in here: {login_url}\n\n"
        "If you didn't sign up, ignore this email."
    )
    return await _safe_send(to_email, subject, html, text, "welcome email")


# ─── Password Reset Email ─────────────────────────────────────────────────────

async def send_password_reset_email(
    to_email: str, first_name: str, reset_link: str, expire_hours: int
) -> bool:
    subject = f"Reset your {settings.APP_NAME} password"
    c = "#4f46e5"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:560px;">

  <!-- HEADER -->
  <tr><td style="background:#1a1a2e;padding:32px 40px;">
    <h1 style="margin:0;color:#fff;font-size:24px;font-weight:700;">{settings.APP_NAME}</h1>
  </td></tr>

  <!-- BODY -->
  <tr><td style="padding:40px 40px 32px;">
    <h2 style="margin:0 0 12px;font-size:20px;color:#1a1a2e;">Password Reset Request</h2>
    <p style="margin:0 0 20px;font-size:15px;color:#555;line-height:1.7;">
      Hi <strong>{first_name}</strong>, we received a request to reset your password.
      This link expires in <strong>{expire_hours} hour{"s" if expire_hours != 1 else ""}</strong>.
    </p>

    <!-- Warning -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
      <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
        <p style="margin:0;font-size:13px;color:#92400e;line-height:1.6;">
          <strong>&#x26A0;&#xFE0F; Didn't request this?</strong><br>
          Ignore this email. Your password won't change and this link expires automatically.
        </p>
      </td></tr>
    </table>

    <!-- CTA -->
    <table cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
      <tr><td style="border-radius:8px;background:{c};">
        <a href="{reset_link}"
           style="display:inline-block;padding:14px 32px;color:#fff;
                  font-size:15px;font-weight:600;text-decoration:none;border-radius:8px;">
          Reset My Password &rarr;
        </a>
      </td></tr>
    </table>

    <!-- Security note -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="background:#f8fafc;border-radius:8px;padding:14px 16px;">
        <p style="margin:0;font-size:13px;color:#555;line-height:1.6;">
          &#x1F512; <strong>Security:</strong> This link works only once and
          expires in {expire_hours}h. We will never ask for your password by email or phone.
        </p>
      </td></tr>
    </table>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="padding:20px 40px;border-top:1px solid #f0f0f0;">
    <p style="margin:0 0 6px;font-size:12px;color:#aaa;line-height:1.6;">
      Button not working? Copy this link:<br>
      <a href="{reset_link}" style="color:{c};word-break:break-all;font-size:12px;">{reset_link}</a>
    </p>
    <p style="margin:8px 0 0;font-size:12px;color:#aaa;">
      Do not share this link with anyone. Sent by {settings.APP_NAME}.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    text = (
        f"Hi {first_name},\n\n"
        f"Reset your {settings.APP_NAME} password (expires in {expire_hours}h):\n\n"
        f"{reset_link}\n\n"
        "If you didn't request this, ignore this email.\n"
        "Your password will NOT change unless you click the link.\n\n"
        f"— {settings.APP_NAME} Team"
    )
    return await _safe_send(to_email, subject, html, text, "password reset email")