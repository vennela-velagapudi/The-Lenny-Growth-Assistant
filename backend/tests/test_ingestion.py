import pytest
from unittest.mock import MagicMock, patch
from app.services.ingestion import IngestionService
import tempfile
import os

@pytest.fixture
def mock_db_session():
    session = MagicMock()
    return session

@pytest.fixture
def mock_embedding_provider():
    provider = MagicMock()
    provider.generate_embeddings.return_value = [[0.1, 0.2, 0.3]]
    return provider

def test_ingestion_hash_idempotency(mock_db_session, mock_embedding_provider):
    with patch('app.services.ingestion.get_embedding_provider', return_value=mock_embedding_provider):
        service = IngestionService(mock_db_session)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write("Hello world test")
            temp_path = f.name
            
        try:
            # Mock DB returning an existing record with the same hash
            existing_mock = MagicMock()
            existing_mock.content_hash = service._compute_hash("Hello world test")
            mock_db_session.exec.return_value.first.return_value = existing_mock
            
            is_new, chunks = service.process_file(temp_path)
            
            assert is_new is False
            assert chunks == 0
            mock_embedding_provider.generate_embeddings.assert_not_called()
        finally:
            os.remove(temp_path)

def test_ingestion_new_file(mock_db_session, mock_embedding_provider):
    with patch('app.services.ingestion.get_embedding_provider', return_value=mock_embedding_provider):
        service = IngestionService(mock_db_session)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write("Hello world test")
            temp_path = f.name
            
        try:
            # Mock DB returning no existing record
            mock_db_session.exec.return_value.first.return_value = None
            
            is_new, chunks = service.process_file(temp_path)
            
            assert is_new is True
            assert chunks == 1
            mock_embedding_provider.generate_embeddings.assert_called_once()
        finally:
            os.remove(temp_path)

def test_ingestion_empty_file(mock_db_session):
    service = IngestionService(mock_db_session)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        f.write("   ")
        temp_path = f.name
    try:
        is_new, chunks = service.process_file(temp_path)
        assert is_new is False
        assert chunks == 0
    finally:
        os.remove(temp_path)
