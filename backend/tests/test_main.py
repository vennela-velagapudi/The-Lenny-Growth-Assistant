from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

def test_health_check():
    # Context manager triggers lifespan, safely mocked
    with patch('app.main.create_db_and_tables') as mock_db:
        with TestClient(app) as test_client:
            response = test_client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            mock_db.assert_called_once()
