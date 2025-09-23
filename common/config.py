import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
    COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY", "")
    COURTLISTENER_BASE_URL = os.getenv("COURTLISTENER_BASE_URL", "https://www.courtlistener.com/api/rest/v4/")

    CASE_FINDER_URL = os.getenv("CASE_FINDER_URL", "http://localhost:8001")
    SUMMARY_URL = os.getenv("SUMMARY_URL", "http://localhost:8002")
    CITATION_URL = os.getenv("CITATION_URL", "http://localhost:8003")
    PRECEDENT_URL = os.getenv("PRECEDENT_URL", "http://localhost:8004")

    JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

    CASE_TYPE_LABELS_URL = os.getenv("CASE_TYPE_LABELS_URL", "")
    TOPIC_LABELS_URL = os.getenv("TOPIC_LABELS_URL", "")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "legal_research")