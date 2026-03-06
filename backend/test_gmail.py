"""
diagnose_email.py

Run this FIRST to find your exact error:
  cd D:\Cold_calling_agent\ai-calling-saas\backend
  python diagnose_email.py
"""

import asyncio
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import socket

load_dotenv()

USER     = os.getenv("SMTP_USER", "").strip()
PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
HOST     = "smtp.gmail.com"


def build_msg(to: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "FastAPI SMTP Test"
    msg["From"]    = USER
    msg["To"]      = to
    msg.attach(MIMEText("SMTP test from FastAPI backend.", "plain"))
    return msg


async def try_config(label, port, use_tls, start_tls, to_email):
    print(f"\n  [{label}] port={port} tls={use_tls} starttls={start_tls}")
    try:
        await aiosmtplib.send(
            build_msg(to_email),
            hostname=HOST, port=port,
            username=USER, password=PASSWORD,
            use_tls=use_tls, start_tls=start_tls,
            timeout=15,
        )
        print(f"  ✅ SUCCESS — use this config!")
        return True
    except aiosmtplib.SMTPAuthenticationError as e:
        print(f"  ❌ AUTH FAILED: {e}")
        print(f"     → Password is wrong. Need App Password (16 chars, no spaces).")
        return "auth"
    except aiosmtplib.SMTPConnectError as e:
        print(f"  ❌ CONNECT FAILED: {e}")
        print(f"     → Port {port} is blocked by your network/firewall.")
        return False
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return False


async def main():
    print("\n" + "="*55)
    print("  EMAIL DIAGNOSTIC")
    print("="*55)
    print(f"  SMTP User    : {USER}")
    print(f"  Password len : {len(PASSWORD)} chars  (should be 16)")
    print(f"  Password     : {'*' * len(PASSWORD)}")

    if not USER:
        print("\n❌ SMTP_USER is empty in .env"); return
    if not PASSWORD:
        print("\n❌ SMTP_PASSWORD is empty in .env"); return

    if len(PASSWORD) != 16:
        print(f"\n⚠️  WARNING: App Password must be exactly 16 chars.")
        print(f"   Yours is {len(PASSWORD)} chars.")
        if " " in os.getenv("SMTP_PASSWORD", ""):
            print("   You have SPACES in the password — remove them!")
            print("   Example: 'abcd efgh ijkl mnop' → 'abcdefghijklmnop'")

    # Check network connectivity first
    print("\n  Checking network connectivity to smtp.gmail.com...")
    for port in [587, 465]:
        try:
            sock = socket.create_connection(("smtp.gmail.com", port), timeout=5)
            sock.close()
            print(f"  ✅ Port {port} is reachable")
        except Exception:
            print(f"  ❌ Port {port} is BLOCKED by your network")

    # Ask where to send the test email
    to_email = input(f"\n  Send test email to (press Enter to use {USER}): ").strip()
    if not to_email:
        to_email = USER

    print(f"\n  Testing all SMTP configurations → sending to {to_email}")

    configs = [
        ("587+STARTTLS", 587, False, True),
        ("465+SSL",      465, True,  False),
        ("587+noTLS",    587, False, False),
    ]

    for label, port, use_tls, start_tls in configs:
        result = await try_config(label, port, use_tls, start_tls, to_email)
        if result is True:
            print(f"\n  ✅ Working config found!")
            print(f"  Update your .env:")
            print(f"    SMTP_PORT={port}")
            print(f"    SMTP_TLS={'true' if use_tls else 'false'}")
            print(f"    SMTP_STARTTLS={'true' if start_tls else 'false'}")
            return
        if result == "auth":
            print("\n  All configs will fail — password issue.")
            print("  Fix the App Password first (see guide below).")
            break

    print("""
GOOGLE WORKSPACE APP PASSWORD GUIDE:
══════════════════════════════════════════════════════
If aiteamlead@tierceindia.com is a Google Workspace (company) email:

OPTION A — Admin enables App Passwords (recommended):
  1. Admin goes to: admin.google.com
  2. Security → Authentication → 2-step verification
  3. Enable for all users or your account
  4. Then YOU go to: myaccount.google.com/apppasswords
  5. Create App Password → copy 16 chars → paste in .env

OPTION B — If admin can't help, use personal Gmail:
  1. Create/use a personal Gmail: yourname@gmail.com
  2. Go to: myaccount.google.com/security
  3. Enable 2-Step Verification
  4. Go to: myaccount.google.com/apppasswords
  5. Create → copy 16-char password → update .env:
     SMTP_USER=yourname@gmail.com
     SMTP_PASSWORD=abcdefghijklmnop
     SMTP_FROM_EMAIL=yourname@gmail.com

OPTION C — Use a free email service (no admin needed):
  See the alternative providers section below.
══════════════════════════════════════════════════════
""")


if __name__ == "__main__":
    asyncio.run(main())