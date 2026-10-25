import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))


class DatabaseConfig:
    HOST = os.getenv('DB_HOST', '127.0.0.1')
    PORT = int(os.getenv('DB_PORT', '3306'))
    USER = os.getenv('DB_USER', 'root')
    PASSWORD = os.getenv('DB_PASSWORD', '')
    DATABASE = os.getenv('DB_NAME', 'universidad_db')


class Config:
    SECRET_KEY = os.getenv('JWT_SECRET', '')
    JWT_SECONDS = 3600
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
    MAX_CONTENT_LENGTH = 16 * 1024
