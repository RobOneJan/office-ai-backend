from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, echo=True)

# Session erzeugen
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tabellen aus models.py erstellen
from app.models import Base

Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("✅ Connection successful, SELECT 1 returned:", result.scalar())