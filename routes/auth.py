from database import SessionLocal
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

@router.post("/login")
def login(data : LoginRequest, response: Response):
    with SessionLocal() as db:
        user = db.query(StaffUser).filter(StaffUser.username == data.username).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail = "Username sau parolă incorectă.")
        if not verify_password(data.password, user.password_hash):
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
        db.add(session)
        db.commit()
        response.set_cookie(
            key="staff_session",
            value=token,
            max_age=8 * 60 * 60,
            httponly=True,
            samesite="strict",
            secure=False,
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
        secure=False,
    )
    response.headers["Cache-Control"] = "no-store"

    return {"message": "Deconectare reușită."}