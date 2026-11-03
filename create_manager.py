"""Create the first manager interactively; never store a default password."""
from getpass import getpass
from database import SessionLocal, initialize_database
from models import StaffUser
from security import hash_password


def main():
    initialize_database()
    username = input("Username manager: ").strip()
    password = getpass("Parola (minimum 10 caractere): ")
    confirmation = getpass("Confirmă parola: ")
    if not username or len(username) > 80 or not 10 <= len(password) <= 256:
        raise SystemExit("Username obligatoriu (maximum 80), parolă între 10 și 256 caractere.")
    if password != confirmation:
        raise SystemExit("Parolele nu coincid.")
    with SessionLocal() as db:
        if db.query(StaffUser).filter(StaffUser.username == username).first():
            raise SystemExit("Username-ul există deja.")
        db.add(StaffUser(username=username, password_hash=hash_password(password), role="MANAGER", is_active=True))
        db.commit()
    print("Contul de manager a fost creat.")


if __name__ == "__main__":
    main()
