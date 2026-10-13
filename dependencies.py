from datetime import datetime, timezone
from hashlib import sha256
from fastapi import Depends, HTTPException, Request
from database import SessionLocal
from models import StaffSession, StaffUser


def get_current_staff(request: Request) -> StaffUser:
    token = request.cookies.get("staff_session")
    if not token:
        raise HTTPException(
            status_code=401, detail="Autentificare necesară."
        )
    token_hash = sha256(token.encode()).hexdigest()
    with SessionLocal() as db:
        session = db.query(StaffSession).filter(
            StaffSession.token_hash == token_hash
        ).first()
        if session is None:
            raise HTTPException(
                status_code=401, detail="Sesiune invalidă."
            )
        expires_at = session.expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=401, detail="Sesiune expirată."
            )
        user = db.get(StaffUser, session.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=401, detail="Cont indisponibil."
            )
        return user


def require_manager(
    user: StaffUser = Depends(get_current_staff),
) -> StaffUser:
    if user.role != "MANAGER":
        raise HTTPException(
            status_code=403,
            detail="Acces permis doar managerului.",
        )

    return user
