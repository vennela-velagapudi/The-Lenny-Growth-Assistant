from sqlmodel import SQLModel, create_engine
from app.core.config import settings
import app.db.models  # noqa: F401

engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
    from sqlmodel import Session, text
    with Session(engine) as session:
        session.exec(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        session.commit()
    SQLModel.metadata.create_all(engine)
