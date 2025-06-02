import os

from dotenv import load_dotenv

load_dotenv()

DB_PORT = int(os.getenv("DB_PORT"))
DB_HOST = os.getenv("DB_HOST")
DATABASE = os.getenv("DATABASE")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")