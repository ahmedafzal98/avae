#!/usr/bin/env python3
"""
Migration script to migrate data from Redis to PostgreSQL

This script reads existing data from Redis and migrates it to the new
PostgreSQL database structure. It handles:
- Task metadata (task:*) -> documents table
- Skips temporary keys like progress:*
- Creates a default user if none exists

Usage:
    python scripts/migrate_redis_to_pg.py [--dry-run]
"""
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import redis
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import SessionLocal, init_db
from app.db_models import User, Document


class RedisToPgMigrator:
    """Migrates data from Redis to PostgreSQL"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        self.stats = {
            "tasks_processed": 0,
            "tasks_migrated": 0,
            "tasks_skipped": 0,
            "errors": 0
        }
    
    def get_or_create_default_user(self, db: Session) -> User:
        """Get or create a default user for migrated documents"""
        default_email = "migrated@system.local"
        default_api_key = "migrated_user_api_key_" + datetime.now().strftime("%Y%m%d")
        
        user = db.query(User).filter(User.email == default_email).first()
        
        if not user:
            user = User(
                email=default_email,
                api_key=default_api_key
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created default user: {default_email}")
        else:
            print(f"ℹ️  Using existing user: {default_email}")
        
        return user
    
    def parse_task_data(self, task_id: str) -> Optional[Dict]:
        """Parse task data from Redis hash"""
        try:
            task_data = self.redis_client.hgetall(f"task:{task_id}")
            if not task_data:
                return None
            
            return task_data
        except Exception as e:
            print(f"❌ Error parsing task {task_id}: {e}")
            return None
    
    def get_result_data(self, task_id: str) -> Optional[str]:
        """Get result text from Redis"""
        try:
            result_json = self.redis_client.get(f"result:{task_id}")
            if result_json:
                result_dict = json.loads(result_json)
                return result_dict.get("text", "")
            return None
        except Exception as e:
            print(f"⚠️  Warning: Could not get result for {task_id}: {e}")
            return None
    
    def migrate_task_to_document(
        self,
        db: Session,
        user: User,
        task_id: str,
        task_data: Dict
    ) -> bool:
        """Migrate a single task to a document record"""
        try:
            # Check if document already exists (by s3_key or task_id)
            s3_key = task_data.get("s3_key", "")
            existing = db.query(Document).filter(
                Document.s3_key == s3_key
            ).first()
            
            if existing:
                print(f"⏭️  Skipping task {task_id}: already exists in database")
                self.stats["tasks_skipped"] += 1
                return False
            
            # Parse timestamps
            created_at = self._parse_timestamp(task_data.get("created_at"))
            started_at = self._parse_timestamp(task_data.get("started_at"))
            completed_at = self._parse_timestamp(task_data.get("completed_at"))
            
            # Get result text if available
            result_text = self.get_result_data(task_id)
            
            # Create document record
            document = Document(
                user_id=user.id,
                filename=task_data.get("filename", "unknown.pdf"),
                s3_key=s3_key,
                status=task_data.get("status", "UNKNOWN"),
                result_text=result_text,
                error_message=task_data.get("error") or None,
                created_at=created_at or datetime.utcnow(),
                started_at=started_at,
                completed_at=completed_at
            )
            
            if not self.dry_run:
                db.add(document)
                db.commit()
                db.refresh(document)
            
            print(f"✅ Migrated task {task_id} -> document ID {document.id if not self.dry_run else 'N/A (dry-run)'}")
            self.stats["tasks_migrated"] += 1
            return True
            
        except Exception as e:
            print(f"❌ Error migrating task {task_id}: {e}")
            self.stats["errors"] += 1
            db.rollback()
            return False
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO format timestamp string to datetime"""
        if not timestamp_str or timestamp_str == "":
            return None
        
        try:
            # Try parsing ISO format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def get_all_task_ids(self) -> List[str]:
        """Get all task IDs from Redis"""
        task_ids = []
        
        # Method 1: Get from all_tasks list
        try:
            task_ids_from_list = self.redis_client.lrange("all_tasks", 0, -1)
            task_ids.extend(task_ids_from_list)
            print(f"📋 Found {len(task_ids_from_list)} tasks from all_tasks list")
        except Exception as e:
            print(f"⚠️  Warning: Could not get tasks from list: {e}")
        
        # Method 2: Scan for task:* keys
        try:
            cursor = 0
            task_keys = []
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="task:*", count=100)
                task_keys.extend(keys)
                if cursor == 0:
                    break
            
            # Extract task IDs from keys
            task_ids_from_keys = [key.replace("task:", "") for key in task_keys]
            
            # Add new task IDs not already in list
            new_ids = set(task_ids_from_keys) - set(task_ids)
            task_ids.extend(new_ids)
            
            if new_ids:
                print(f"📋 Found {len(new_ids)} additional tasks from key scan")
        except Exception as e:
            print(f"⚠️  Warning: Could not scan for task keys: {e}")
        
        return list(set(task_ids))  # Remove duplicates
    
    def migrate(self):
        """Run the migration"""
        print("=" * 70)
        print("Redis to PostgreSQL Migration Script")
        print("=" * 70)
        
        if self.dry_run:
            print("🔍 DRY RUN MODE - No data will be written to database")
            print()
        
        # Initialize database
        print("📊 Initializing database...")
        try:
            init_db()
            print("✅ Database initialized")
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            return False
        
        # Check Redis connection
        print("\n🔌 Checking Redis connection...")
        try:
            self.redis_client.ping()
            print("✅ Connected to Redis")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            return False
        
        # Get all task IDs
        print("\n🔍 Scanning for tasks in Redis...")
        task_ids = self.get_all_task_ids()
        print(f"📊 Found {len(task_ids)} total tasks")
        
        if not task_ids:
            print("ℹ️  No tasks found to migrate")
            return True
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Get or create default user
            print("\n👤 Setting up default user...")
            user = self.get_or_create_default_user(db)
            
            # Migrate each task
            print(f"\n🚀 Starting migration of {len(task_ids)} tasks...")
            print("-" * 70)
            
            for i, task_id in enumerate(task_ids, 1):
                self.stats["tasks_processed"] += 1
                
                # Skip progress keys and other temporary keys
                if task_id.startswith("progress:") or task_id.startswith("result:"):
                    self.stats["tasks_skipped"] += 1
                    continue
                
                # Parse task data
                task_data = self.parse_task_data(task_id)
                if not task_data:
                    print(f"⏭️  Skipping task {task_id}: no data found")
                    self.stats["tasks_skipped"] += 1
                    continue
                
                # Migrate task
                self.migrate_task_to_document(db, user, task_id, task_data)
                
                # Progress update
                if i % 10 == 0:
                    print(f"📊 Progress: {i}/{len(task_ids)} tasks processed")
            
            print("-" * 70)
            
        finally:
            db.close()
        
        # Print summary
        print("\n" + "=" * 70)
        print("Migration Summary")
        print("=" * 70)
        print(f"Tasks Processed:  {self.stats['tasks_processed']}")
        print(f"Tasks Migrated:   {self.stats['tasks_migrated']}")
        print(f"Tasks Skipped:    {self.stats['tasks_skipped']}")
        print(f"Errors:           {self.stats['errors']}")
        print("=" * 70)
        
        if self.dry_run:
            print("\n🔍 DRY RUN COMPLETE - No changes were made")
        else:
            print("\n✅ MIGRATION COMPLETE")
        
        return self.stats["errors"] == 0


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate data from Redis to PostgreSQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode without writing to database"
    )
    
    args = parser.parse_args()
    
    migrator = RedisToPgMigrator(dry_run=args.dry_run)
    success = migrator.migrate()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
