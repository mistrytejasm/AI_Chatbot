from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # API Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # AI Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    MODEL_NAME: str = "openai/gpt-oss-120b"
    MODEL_TEMPERATURE: float = 0.1

    # Search Configuration
    MAX_SEARCH_RESULTS: int = 3
    SEARCH_TIMEOUT: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
