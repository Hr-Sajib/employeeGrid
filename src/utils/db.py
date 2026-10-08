import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.utils.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = create_engine(url=settings.DB_CONNECTION)

try:
    with engine.connect() as connection:
        logger.info("✅ Database connected successfully!")
except Exception as e:
    logger.error(f"❌ Failed to connect to database: {e}")

Session = sessionmaker(bind=engine)

def get_db():
    session = Session()
    try:
        yield session
    finally:
        session.close()
