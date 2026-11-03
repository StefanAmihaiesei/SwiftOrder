from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from dependencies import require_manager
from models import StaffUser, StaffSession
from schemas import StaffCreate, StaffUpdate
from security import hash_password

router = APIRouter(prefix="/staff", tags=["Personal"])


def public_user(user):
    return {"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active}


@router.get("")
def list_staff(manager=Depends(require_manager)):
    with SessionLocal() as db:
        return [public_user(user) for user in db.query(StaffUser).order_by(StaffUser.id)]


@router.post("", status_code=201)
def create_staff(data: StaffCreate, manager=Depends(require_manager)):
    with SessionLocal() as db:
        user = StaffUser(username=data.username, password_hash=hash_password(data.password), role=data.role, is_active=True)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Username-ul există deja.")
        return public_user(user)


@router.patch("/{user_id}")
def update_staff(user_id: int, data: StaffUpdate, manager=Depends(require_manager)):
    if user_id == manager.id:
        raise HTTPException(409, "Nu îți poți dezactiva propriul cont.")
    with SessionLocal() as db:
        user = db.get(StaffUser, user_id)
        if user is None:
            raise HTTPException(404, "Cont inexistent.")
        user.is_active = data.is_active
        if not data.is_active:
            db.query(StaffSession).filter(StaffSession.user_id == user_id).delete()
        db.commit()
        return public_user(user)
