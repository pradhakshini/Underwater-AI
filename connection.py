"""Database connection management."""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from backend.utils.config import settings
from backend.utils.logging_utils import get_logger

logger = get_logger("database")

# MongoDB connection
client: Optional[AsyncIOMotorClient] = None
database = None


async def connect_to_mongo():
    """Create database connection."""
    global client, database
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = client[settings.MONGODB_DB_NAME]
        # Test connection
        await client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close database connection."""
    global client
    if client:
        client.close()
        logger.info("Disconnected from MongoDB")


def get_database():
    """Get database instance."""
    return database


# PostgreSQL alternative (commented out)
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker
# 
# engine = None
# async_session = None
# 
# async def connect_to_postgres():
#     """Create PostgreSQL connection."""
#     global engine, async_session
#     try:
#         engine = create_async_engine(
#             settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
#             echo=True
#         )
#         async_session = sessionmaker(
#             engine, class_=AsyncSession, expire_on_commit=False
#         )
#         logger.info("Connected to PostgreSQL")
#     except Exception as e:
#         logger.error(f"Failed to connect to PostgreSQL: {e}")
#         raise
# 
# async def close_postgres_connection():
#     """Close PostgreSQL connection."""
#     global engine
#     if engine:
#         await engine.dispose()
#         logger.info("Disconnected from PostgreSQL")
# 
# async def get_postgres_session():
#     """Get PostgreSQL session."""
#     async with async_session() as session:
#         yield session
