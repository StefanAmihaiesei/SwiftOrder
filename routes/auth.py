from database import SessionLocal
from config import COOKIE_SECURE
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from security import hash_password
from schemas import LoginRequest
from security import verify_password
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from models import StaffUser, StaffSession
from fastapi import Depends
from dependencies import get_current_staff
from fastapi import APIRouter, HTTPException, Response, Request

router = APIRouter(prefix = "/auth", tags = ["Autentificare"])

# Single-process local MVP limiter. Use an edge/shared limiter with multiple workers.
login_attempts = defaultdict(deque)
login_lock = Lock()
dummy_hash = hash_password("unused-timing-equalizer")


def limit_login(request):
    address = request.client.host if request.client else "unknown"
    now = monotonic()
    with login_lock:
        for key in list(login_attempts):
            if not login_attempts[key] or login_attempts[key][-1] <= now - 60:
                del login_attempts[key]
        attempts = login_attempts[address]
        while attempts and attempts[0] <= now - 60:
            attempts.popleft()
        if len(attempts) >= 10:
            raise HTTPException(429, "Prea multe încercări. Așteaptă un minut.", headers={"Retry-After": "60"})
        attempts.append(now)


@router.post("/login")
def login(data: LoginRequest, response: Response, request: Request):
    limit_login(request)
    with SessionLocal() as db:
        user = db.query(StaffUser).filter(StaffUser.username == data.username).first()
        password_valid = verify_password(data.password, user.password_hash if user else dummy_hash)
        if user is None or not user.is_active or not password_valid:
            raise HTTPException(status_code=401, detail = "Username sau parolă incorectă.")
        token = token_urlsafe(32)
        token_hash = sha256(token.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        session = StaffSession(
            user_id=user.id,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + timedelta(hours=8),
        )
        db.query(StaffSession).filter(StaffSession.expires_at <= now).delete()
        old_token = request.cookies.get("staff_session")
        if old_token:
            db.query(StaffSession).filter(StaffSession.token_hash == sha256(old_token.encode()).hexdigest()).delete()
        db.add(session)
        db.commit()
        response.set_cookie(
            key="staff_session",
            value=token,
            max_age=8 * 60 * 60,
            httponly=True,
            samesite="strict",
            secure=COOKIE_SECURE,
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return {
            "message": "Date de autentificare corecte!",
            "username": user.username,
            "role": user.role,
        }
@router.get("/me")
def get_me(user: StaffUser = Depends(get_current_staff)):
    return {
        "username": user.username,
        "role": user.role,
    }
@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("staff_session")

    if token:
        token_hash = sha256(token.encode()).hexdigest()

        with SessionLocal() as db:
            session = db.query(StaffSession).filter(
                StaffSession.token_hash == token_hash
            ).first()

            if session is not None:
                db.delete(session)
                db.commit()

    response.delete_cookie(
        key="staff_session",
        path="/",
        httponly=True,
        samesite="strict",
        secure=COOKIE_SECURE,
    )
    response.headers["Cache-Control"] = "no-store"

    return {"message": "Deconectare reușită."}