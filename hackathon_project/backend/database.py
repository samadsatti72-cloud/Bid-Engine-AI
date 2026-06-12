import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

# Initialize database engine with connection pool settings
engine = create_engine(
    DATABASE_URL,
    pool_size=5,           # Number of connections kept open
    max_overflow=10,       # Extra connections allowed above pool_size
    pool_timeout=30,       # Seconds to wait for a connection before error
    pool_pre_ping=True,    # Verify connections before use (prevents stale conn errors)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
