import pytest
from app.db.database import engine
from sqlmodel import Session, text
import sqlalchemy

def is_db_available():
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        return True
    except Exception:
        return False

@pytest.mark.skipif(not is_db_available(), reason="PostgreSQL not available")
def test_pgvector_similarity():
    # This integration test verifies that pgvector is installed and functioning
    with Session(engine) as session:
        # We assume the database has been migrated.
        try:
            # We won't insert real data, just ensure we can query using distance
            session.exec(text("SELECT '[1,2,3]'::vector <=> '[3,2,1]'::vector"))
        except sqlalchemy.exc.ProgrammingError as e:
            pytest.fail(f"pgvector query failed: {e}")
