from sqlalchemy import create_engine
from sqlalchemy.orm import Session

SQLALCHEMY_DATABASE_URL = "sqlite:///./storage.db"

# engine vytvoří spojení s databází
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=True
)

# Pomocná funkce, kterou pak použijeme ve FastAPI pro získání session
def get_db():
    with Session(engine) as session:
        yield session