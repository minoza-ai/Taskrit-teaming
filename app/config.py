import os

from dotenv import load_dotenv

load_dotenv()

class Settings:
    """앱 전역 설정."""

    geminiApi: str = os.getenv("GEMINI_API", "")
    mongoUri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongoDbName: str = os.getenv("MONGODB_DB", "taskrit")
    qdrantHost: str = os.getenv("QDRANT_HOST", "localhost")
    qdrantPort: int = int(os.getenv("QDRANT_PORT", "6333"))
    hmacKey: str = os.getenv("HMAC_KEY", "")
    embeddingDim: int = 3072  # Gemini embedding dimension

settings = Settings()
