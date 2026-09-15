from sqlmodel import SQLModel, create_engine
from app.core.config import settings
import app.db.models  # noqa: F401

engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
    from sqlmodel import Session, text
    try:
        with Session(engine) as session:
            session.exec(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            session.commit()
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.warning("Could not create vector extension, skipping", error=str(e))
    # Note: We now rely on Alembic for creating tables.

def get_session():
    from sqlmodel import Session
    with Session(engine) as session:
        yield session
