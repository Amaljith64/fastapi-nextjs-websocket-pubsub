import os
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

print(BASE_DIR,'this is the base dir')

UPLOAD_DIR = BASE_DIR / "uploads"
CONVERTED_DIR = BASE_DIR / "converted"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CONVERTED_DIR.mkdir(parents=True, exist_ok=True)


DATABASE_USERNAME = os.getenv("DB_USER", "yourusername")
DATABASE_PASSWORD = os.getenv("DB_PASSWORD", "yourpassword")
DATABASE_NAME = os.getenv("DB_NAME", "databasename")
DATABASE_HOST = os.getenv("DB_HOST", "db")  
RABBITMQ_USER = os.getenv('RABBITMQ_USER','imgconv')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS','imgconv123')

class Settings(BaseSettings):
    # File handling settings
    UPLOAD_DIR: Path = UPLOAD_DIR
    CONVERTED_DIR: Path = CONVERTED_DIR
    MAX_FILE_SIZE: int = 10_000_000  # 10MB
    ALLOWED_FORMATS: List[str] = ["jpg", "jpeg", "png", "gif", "webp"]
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Database settings
    DB_USER: str = os.getenv("DB_USER", "yourusername")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "yourpassword")
    DB_NAME: str = os.getenv("DB_NAME", "databasename")
    DB_HOST: str = os.getenv("DB_HOST", "db")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    
    # RabbitMQ settings
    RABBITMQ_USER: str = os.getenv('RABBITMQ_USER', 'imgconv')
    RABBITMQ_PASS: str = os.getenv('RABBITMQ_PASS', 'imgconv123')

    #Redis settings
    REDIS_HOST: str = os.getenv('REDIS_HOST','redis') 
    REDIS_PORT: str =os.getenv('REDIS_PORT','6379') 
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}"

    #rate limit settings
    RATE_LIMIT_DURATION: str =os.getenv('RATE_LIMIT_DURATION','60')
    MAX_REQUESTS: int =os.getenv('MAX_REQUESTS',10)

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    


    class Config:
        env_file = ".env"
        case_sensitive = False

