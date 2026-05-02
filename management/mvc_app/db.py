import os
from sqlalchemy import create_engine
try:
    from sqlalchemy.orm import declarative_base, sessionmaker
except Exception:
    # older SQLAlchemy versions
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://appuser:apassword@db:5432/appdb")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def create_tables():
    Base.metadata.create_all(bind=engine)

