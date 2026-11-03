from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
)

@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    dbapi_connection.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine)


def initialize_database():
    """Create missing tables and apply the additive SQLite upgrade."""
    from models import Base
    from sqlalchemy import inspect, text
    Base.metadata.create_all(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("order_items")}
    if "product_name" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE order_items ADD COLUMN product_name VARCHAR"))
