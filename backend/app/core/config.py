import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LLM_PROVIDER: str = "ollama"
    OLLAMA_URL: str = "http://localhost:11434"
    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/lenny_db"
    
    class Config:
        env_file = ".env"

settings = Settings()
