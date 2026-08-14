import os

from fastapi import Header, HTTPException

from app.db import get_db


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("ADMIN_API_TOKEN")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")

