from getpass import getpass

from database import SessionLocal
from models import StaffUser
from security import hash_password

username = input("Username manager: ").strip()
password = getpass("Parola: ")
confirmation = getpass("Confirma parola: ")

if not username or not password:
    print("Username-ul si parola sunt obligatorii!")
elif password != confirmation:
    print("Parolele nu coincid!")
else:
    with SessionLocal() as db:
        existing_user = db.query(StaffUser).filter(
            StaffUser.username == username
        ).first()
        if existing_user:
            print("Username-ul exista deja!")
        else:
            manager = StaffUser(username = username, password_hash = hash_password(password), role = "MANAGER", is_active = True)
            db.add(manager)
            db.commit()
            print("Contul de manager a fost creat.")
