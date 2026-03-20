"""
LangGraph PostgreSQL checkpointer (Task 3.2).

Creates checkpoints and checkpoint_writes tables for graph state persistence.
Enables resume after failures and HITL (Phase 5).

Requires: psycopg[binary]>=3.2.0, psycopg-pool>=3.2.0
"""
import logging
from app.config import settings

logger = logging.getLogger(__name__)

_checkpointer = None


def get_checkpointer():
    """
    Get or create the PostgresSaver checkpointer.

    Uses ConnectionPool for long-lived process. Calls setup() on first use to create
    checkpoints and checkpoint_writes tables.
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    conn_string = settings.database_url
    if not conn_string or conn_string.startswith("postgresql+asyncpg"):
        logger.warning("Checkpointer requires sync PostgreSQL URL (postgresql://)")
        return None

    # Normalize postgres:// to postgresql:// for psycopg
    if conn_string.startswith("postgres://"):
        conn_string = conn_string.replace("postgres://", "postgresql://", 1)

    try:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError as e:
        logger.warning(
            "LangGraph Postgres checkpointer not available: %s. "
            "Install: pip install psycopg[binary] psycopg-pool",
            e,
        )
        return None

    try:
        pool = ConnectionPool(
            conn_string,
            max_size=10,
            min_size=1,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )
        _checkpointer = PostgresSaver(pool)
        _checkpointer.setup()
        logger.info("✅ LangGraph Postgres checkpointer initialized")
        return _checkpointer
    except Exception as e:
        logger.error("Failed to create Postgres checkpointer: %s", e)
        return None
