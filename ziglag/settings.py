import os
from pathlib import Path

import stk

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Config(stk.Config):
    APP_NAME = os.environ.get("APP_NAME", "ZigLag")
    APP_TAGLINE = os.environ.get("APP_TAGLINE", "Self-hosted invoicing")
    APP_DESCRIPTION = os.environ.get("APP_DESCRIPTION", "Self-hosted invoicing")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        f"sqlite+aiosqlite:///{PROJECT_ROOT / 'instance' / 'ziglag.db'}",
    )

    STK_CLI_SECTIONS = [("Backup", ["backup"]), ("Upgrade", ["adopt-stk16"])]

    # Accounts are created by /setup and by admins, never by public sign-up.
    SECURITY_REGISTERABLE = False
    SECURITY_PASSWORD_LENGTH_MIN = int(
        os.environ.get("SECURITY_PASSWORD_LENGTH_MIN", 12)
    )
    SECURITY_TOTP_ISSUER = "ZigLag"
    SECURITY_EMAIL_SENDER = os.environ.get(
        "SECURITY_EMAIL_SENDER", "noreply@ziglag.com"
    )
