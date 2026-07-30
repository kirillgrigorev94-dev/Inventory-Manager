import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db.sqlite3")
    SECRET_KEY = os.getenv("SECRET_KEY", "change_me")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    EXPIRING_SOON_DAYS = int(os.getenv("EXPIRING_SOON_DAYS", "3"))

settings = Settings()