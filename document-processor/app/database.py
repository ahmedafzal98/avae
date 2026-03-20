"""Database configuration and session management using SQLAlchemy 2.0"""
import logging
from sqlalchemy import create_engine, text, Index
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator, Generator

from app.config import settings

logger = logging.getLogger(__name__)


# SQLAlchemy 2.0 Declarative Base
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


# Create database engine with connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug_sql  # Set to True for SQL query logging
)

# Create SessionLocal class for database sessions (sync — used by sqs_worker)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session
)

# ---------------------------------------------------------------------------
# Async engine + session factory (used by FastAPI endpoints)
# ---------------------------------------------------------------------------

_async_connect_args = {"ssl": True} if settings.requires_ssl else {}
async_engine = create_async_engine(
    settings.async_database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug_sql,
    connect_args=_async_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency for FastAPI endpoints to get a non-blocking database session.

    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    async with AsyncSessionLocal() as session:
        yield session


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get a database session
    
    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables and extensions
    
    Creates all tables defined in models that inherit from Base.
    Also ensures pgvector extension is installed for vector operations.
    
    HNSW Index Creation:
    - SQLAlchemy will attempt to create HNSW indexes defined in models
    - For large datasets (>1000 chunks), this can take 5-30 minutes
    - If your app takes too long to start, use migrations/run_migration.py instead
    - The function checks if indexes exist to avoid rebuilding on every startup
    
    Should be called on application startup.
    """
    logger.info("🔧 Initializing database...")
    
    try:
        with engine.connect() as conn:
            # Step 1: Ensure pgvector extension is installed
            logger.info("📦 Checking pgvector extension...")
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                logger.info("✅ pgvector extension ready")
            except Exception as e:
                logger.warning(f"⚠️  Could not create pgvector extension: {e}")
                logger.warning("   This may be a permissions issue - extension might already exist")
        
        # Step 2: Import models to register them with Base
        from app.db_models import User, Document, DocumentChunk, AuditLog
        
        # Step 3: Check if HNSW index already exists
        index_exists = False
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE tablename = 'document_chunks' 
                        AND indexname = 'idx_chunks_embedding_hnsw'
                    )
                """))
                index_exists = result.scalar()
        except Exception as e:
            logger.warning(f"Could not check for existing HNSW index: {e}")
        
        # Step 4: Create tables (and indexes if they don't exist)
        if index_exists:
            logger.info("✅ HNSW index already exists - skipping index creation")
            # Create tables but skip index creation by temporarily removing it
            # This prevents long startup times when index already exists
            original_table_args = DocumentChunk.__table_args__
            
            # Filter out HNSW index from table args
            filtered_args = tuple(
                arg for arg in original_table_args 
                if not (isinstance(arg, Index) and arg.name == "idx_chunks_embedding_hnsw")
            )
            DocumentChunk.__table_args__ = filtered_args
            
            Base.metadata.create_all(bind=engine)
            
            # Restore original table args
            DocumentChunk.__table_args__ = original_table_args
            
            logger.info("✅ Database tables ready")
        else:
            logger.info("🔨 Creating database tables and indexes...")
            logger.info("⚠️  HNSW index creation may take 5-30 minutes for large datasets")
            logger.info("   If this takes too long, press Ctrl+C and run: python3 migrations/run_migration.py")
            
            # Create all tables and indexes (including HNSW)
            Base.metadata.create_all(bind=engine)
            
            logger.info("✅ Database initialized successfully")
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
