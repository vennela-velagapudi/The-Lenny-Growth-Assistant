import os
import argparse
from sqlmodel import Session
from app.db.database import engine
from app.services.ingestion import IngestionService
import structlog

logger = structlog.get_logger()

def run_ingestion(data_dir: str):
    print("Lenny Transcript Ingestion")
    print("--------------------------")
    
    if not os.path.isdir(data_dir):
        print(f"Error: Directory '{data_dir}' not found.")
        return

    files = [f for f in os.listdir(data_dir) if f.endswith(".md") or f.endswith(".txt")]
    print(f"Files discovered: {len(files)}")
    
    new_sources = 0
    updated_sources = 0
    skipped_unchanged = 0
    chunks_created = 0
    embedding_failures = 0
    
    with Session(engine) as session:
        service = IngestionService(session)
        for f in files:
            file_path = os.path.join(data_dir, f)
            try:
                is_new_or_updated, chunks = service.process_file(file_path)
                if not is_new_or_updated:
                    skipped_unchanged += 1
                elif chunks > 0:
                    new_sources += 1 # We can't distinguish new vs updated easily without changing return sig, assuming new for stats
                    chunks_created += chunks
            except Exception as e:
                logger.error("ingestion_failed", file=f, error=str(e))
                embedding_failures += 1
                print(f"Error processing {f}: {e}")

    print(f"New/Updated sources: {new_sources}")
    print(f"Skipped unchanged: {skipped_unchanged}")
    print(f"Chunks created: {chunks_created}")
    print(f"Embedding failures: {embedding_failures}")
    print("\nIngestion completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Lenny's transcripts")
    parser.add_argument("--dir", default="../../data/transcripts", help="Directory containing transcripts")
    args = parser.parse_args()
    
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), args.dir))
    run_ingestion(target_dir)
