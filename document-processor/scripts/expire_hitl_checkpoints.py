#!/usr/bin/env python3
"""
Expire HITL checkpoints older than TTL days (Task 5.5).

Run via cron, e.g. daily at 2am:
    0 2 * * * cd /path/to/document-processor && python3 scripts/expire_hitl_checkpoints.py
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure .env is loaded from project root (pydantic_settings loads from cwd; this helps when run from elsewhere)
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass


def main():
    from app.hitl_service import expire_hitl_checkpoints

    result = expire_hitl_checkpoints()
    count = result.get("expired_count", 0)
    print(f"Expired {count} HITL checkpoints")
    return 0 if count >= 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
