"""Optional sample menu and tables. Refuses to seed an existing menu."""
from uuid import uuid4
from database import SessionLocal, initialize_database
from models import Product, RestaurantTable


def main():
    initialize_database()
    with SessionLocal() as db:
        if db.query(Product.id).first() or db.query(RestaurantTable.id).first():
            raise SystemExit("Baza conține deja produse sau mese; datele existente au fost păstrate.")
        for name, price, category in [
            ("Espresso", 10, "Băuturi calde"), ("Cappuccino", 16, "Băuturi calde"),
            ("Limonadă", 18, "Băuturi reci"), ("Pizza Margherita", 35, "Pizza"),
            ("Croissant", 12, "Patiserie"), ("Cheesecake", 24, "Deserturi"),
        ]:
            db.add(Product(name=name, price=price, category=category, available=1))
        for number in range(1, 6):
            db.add(RestaurantTable(number=number, qr_token=str(uuid4())))
        db.commit()
    print("Meniul demonstrativ și 5 mese au fost create. Creează managerul cu python create_manager.py.")


if __name__ == "__main__":
    main()
