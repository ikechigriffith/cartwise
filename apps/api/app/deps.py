import os

from fastapi import Header, HTTPException

from app.db import SessionLocal


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("ADMIN_API_TOKEN")
    if expected and x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
