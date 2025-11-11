"""Configuration helpers for credentials and runtime settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Credentials:
    username: Optional[str]
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None


def load_credentials(env_file: Optional[Path] = None) -> Credentials:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()
    username = os.getenv("WEBOT_USERNAME") or None
    password = os.getenv("WEBOT_PASSWORD")
    email = os.getenv("WEBOT_EMAIL") or None
    phone = os.getenv("WEBOT_PHONE") or None

    if not password:
        raise RuntimeError("WEBOT_PASSWORD must be set in environment or .env file")
    if not any([username, email, phone]):
        raise RuntimeError("At least one of WEBOT_USERNAME, WEBOT_EMAIL, or WEBOT_PHONE must be provided")

    return Credentials(username=username, password=password, email=email, phone=phone)
