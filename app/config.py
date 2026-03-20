import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """앱 전역 설정."""

    geminiApi: str = os.getenv("GEMINI_API", "")
    databaseUrl: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./taskrit.db")
    qdrantHost: str = os.getenv("QDRANT_HOST", "localhost")
    qdrantPort: int = int(os.getenv("QDRANT_PORT", "6333"))
    embeddingDim: int = 768  # Gemini embedding dimension


settings = Settings()
