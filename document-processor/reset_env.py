#!/usr/bin/env python3
"""
🚨 DANGER ZONE: Complete Environment Reset Utility 🚨

This script COMPLETELY WIPES all test data across your entire stack:
- PostgreSQL: Truncates documents, document_chunks, and users tables
- Redis: Deletes all task-related keys
- AWS S3: Deletes all uploaded PDFs
- AWS SQS: Purges all queued messages

⚠️  WARNING: This is DESTRUCTIVE and IRREVERSIBLE!
⚠️  DO NOT RUN IN PRODUCTION!

Usage:
    python3 reset_env.py              # Interactive mode with safety prompts
    python3 reset_env.py --dry-run    # Show what would be deleted without deleting
    python3 reset_env.py --force      # Skip confirmation (USE WITH CAUTION!)
"""

import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'reset_env_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class EnvironmentReset:
    """Handles complete environment reset across all services"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'postgres': {'documents': 0, 'chunks': 0, 'users': 0},
            'redis': {'keys_deleted': 0},
            's3': {'objects_deleted': 0},
            'sqs': {'messages_purged': 0}
        }
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will actually be deleted")
    
    def reset_postgresql(self, reset_users: bool = False) -> bool:
        """
        Reset PostgreSQL tables
        
        Args:
            reset_users: If True, also truncate users table (deletes all users)
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info("\n" + "="*60)
            logger.info("🗄️  POSTGRESQL RESET")
            logger.info("="*60)
            
            from sqlalchemy import create_engine, text
            from app.config import settings
            
            engine = create_engine(settings.database_url)
            
            with engine.connect() as conn:
                # Count records before deletion
                logger.info("📊 Counting records before deletion...")
                
                result = conn.execute(text("SELECT COUNT(*) FROM documents"))
                doc_count = result.scalar()
                self.stats['postgres']['documents'] = doc_count
                logger.info(f"   📄 Documents: {doc_count}")
                
                result = conn.execute(text("SELECT COUNT(*) FROM document_chunks"))
                chunk_count = result.scalar()
                self.stats['postgres']['chunks'] = chunk_count
                logger.info(f"   📦 Document chunks: {chunk_count}")
                
                if reset_users:
                    result = conn.execute(text("SELECT COUNT(*) FROM users"))
                    user_count = result.scalar()
                    self.stats['postgres']['users'] = user_count
                    logger.info(f"   👤 Users: {user_count}")
                
                if self.dry_run:
                    logger.info("🔍 [DRY RUN] Would truncate tables")
                    return True
                
                # Truncate tables with CASCADE
                logger.info("\n🗑️  Truncating tables...")
                
                if reset_users:
                    # Truncate users (will cascade to documents and chunks)
                    logger.info("   Truncating users (CASCADE to documents and chunks)...")
                    conn.execute(text("TRUNCATE TABLE users CASCADE"))
                    conn.commit()
                    logger.info("   ✅ Users, documents, and chunks truncated")
                else:
                    # Only truncate documents (will cascade to chunks)
                    logger.info("   Truncating documents (CASCADE to chunks)...")
                    conn.execute(text("TRUNCATE TABLE documents CASCADE"))
                    conn.commit()
                    logger.info("   ✅ Documents and chunks truncated")
                
                # Verify deletion
                result = conn.execute(text("SELECT COUNT(*) FROM documents"))
                remaining_docs = result.scalar()
                
                result = conn.execute(text("SELECT COUNT(*) FROM document_chunks"))
                remaining_chunks = result.scalar()
                
                logger.info(f"\n✅ PostgreSQL reset complete!")
                logger.info(f"   📄 Documents deleted: {doc_count} (remaining: {remaining_docs})")
                logger.info(f"   📦 Chunks deleted: {chunk_count} (remaining: {remaining_chunks})")
                
                if reset_users:
                    result = conn.execute(text("SELECT COUNT(*) FROM users"))
                    remaining_users = result.scalar()
                    logger.info(f"   👤 Users deleted: {user_count} (remaining: {remaining_users})")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ PostgreSQL reset failed: {e}")
            return False
    
    def reset_redis(self) -> bool:
        """
        Reset Redis task-related keys
        
        Deletes keys matching patterns:
        - task:*
        - result:*
        - progress:*
        - rate_limit:*
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info("\n" + "="*60)
            logger.info("🔴 REDIS RESET")
            logger.info("="*60)
            
            import redis
            from app.config import settings
            
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True
            )
            
            # Patterns to delete
            patterns = ['task:*', 'result:*', 'progress:*', 'rate_limit:*']
            total_deleted = 0
            
            for pattern in patterns:
                logger.info(f"\n🔍 Scanning for keys matching: {pattern}")
                keys = list(redis_client.scan_iter(match=pattern, count=1000))
                key_count = len(keys)
                
                if key_count > 0:
                    logger.info(f"   Found {key_count} keys")
                    
                    if self.dry_run:
                        logger.info(f"   🔍 [DRY RUN] Would delete {key_count} keys")
                    else:
                        # Delete in batches
                        if keys:
                            deleted = redis_client.delete(*keys)
                            logger.info(f"   ✅ Deleted {deleted} keys")
                            total_deleted += deleted
                else:
                    logger.info(f"   No keys found")
            
            self.stats['redis']['keys_deleted'] = total_deleted
            
            if not self.dry_run:
                logger.info(f"\n✅ Redis reset complete! Total keys deleted: {total_deleted}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Redis reset failed: {e}")
            return False
    
    def reset_s3(self) -> bool:
        """
        Reset S3 bucket - delete all objects
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info("\n" + "="*60)
            logger.info("☁️  AWS S3 RESET")
            logger.info("="*60)
            
            import boto3
            from app.config import settings
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
            
            bucket_name = settings.s3_bucket_name
            logger.info(f"🪣 Bucket: {bucket_name}")
            
            # List all objects
            logger.info("📋 Listing objects...")
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name)
            
            objects_to_delete = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects_to_delete.append({'Key': obj['Key']})
            
            object_count = len(objects_to_delete)
            logger.info(f"   Found {object_count} objects")
            
            if object_count == 0:
                logger.info("   ✅ Bucket is already empty")
                return True
            
            # Show sample of files to be deleted
            if object_count > 0:
                logger.info("\n📄 Sample of objects to delete:")
                for obj in objects_to_delete[:5]:
                    logger.info(f"   - {obj['Key']}")
                if object_count > 5:
                    logger.info(f"   ... and {object_count - 5} more")
            
            if self.dry_run:
                logger.info(f"\n🔍 [DRY RUN] Would delete {object_count} objects from S3")
                self.stats['s3']['objects_deleted'] = object_count
                return True
            
            # Delete objects in batches (max 1000 per request)
            logger.info(f"\n🗑️  Deleting {object_count} objects...")
            deleted_count = 0
            
            batch_size = 1000
            for i in range(0, len(objects_to_delete), batch_size):
                batch = objects_to_delete[i:i + batch_size]
                response = s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': batch}
                )
                
                deleted = len(response.get('Deleted', []))
                deleted_count += deleted
                logger.info(f"   ✅ Batch {i//batch_size + 1}: Deleted {deleted} objects")
                
                # Check for errors
                if 'Errors' in response and response['Errors']:
                    for error in response['Errors']:
                        logger.error(f"   ❌ Error deleting {error['Key']}: {error['Message']}")
            
            self.stats['s3']['objects_deleted'] = deleted_count
            logger.info(f"\n✅ S3 reset complete! Objects deleted: {deleted_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ S3 reset failed: {e}")
            return False
    
    def reset_sqs(self) -> bool:
        """
        Reset SQS queue - purge all messages
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info("\n" + "="*60)
            logger.info("📨 AWS SQS RESET")
            logger.info("="*60)
            
            import boto3
            from app.config import settings
            
            sqs_client = boto3.client(
                'sqs',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
            
            queue_url = settings.sqs_queue_url
            logger.info(f"📬 Queue URL: {queue_url}")
            
            # Get queue attributes to see message count
            logger.info("📊 Checking queue status...")
            attributes = sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
            )
            
            visible_msgs = int(attributes['Attributes'].get('ApproximateNumberOfMessages', 0))
            invisible_msgs = int(attributes['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))
            total_msgs = visible_msgs + invisible_msgs
            
            logger.info(f"   📨 Visible messages: {visible_msgs}")
            logger.info(f"   👻 In-flight messages: {invisible_msgs}")
            logger.info(f"   📊 Total messages: {total_msgs}")
            
            if total_msgs == 0:
                logger.info("   ✅ Queue is already empty")
                return True
            
            if self.dry_run:
                logger.info(f"\n🔍 [DRY RUN] Would purge {total_msgs} messages from SQS")
                self.stats['sqs']['messages_purged'] = total_msgs
                return True
            
            # Purge queue
            logger.info(f"\n🗑️  Purging {total_msgs} messages...")
            sqs_client.purge_queue(QueueUrl=queue_url)
            
            self.stats['sqs']['messages_purged'] = total_msgs
            logger.info(f"✅ SQS queue purged successfully!")
            logger.info(f"   Note: Messages may take up to 60 seconds to be fully cleared")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ SQS reset failed: {e}")
            return False
    
    def print_summary(self):
        """Print summary of what was deleted"""
        logger.info("\n" + "="*60)
        logger.info("📊 RESET SUMMARY")
        logger.info("="*60)
        
        logger.info(f"\n🗄️  PostgreSQL:")
        logger.info(f"   📄 Documents deleted: {self.stats['postgres']['documents']}")
        logger.info(f"   📦 Chunks deleted: {self.stats['postgres']['chunks']}")
        if self.stats['postgres']['users'] > 0:
            logger.info(f"   👤 Users deleted: {self.stats['postgres']['users']}")
        
        logger.info(f"\n🔴 Redis:")
        logger.info(f"   🔑 Keys deleted: {self.stats['redis']['keys_deleted']}")
        
        logger.info(f"\n☁️  AWS S3:")
        logger.info(f"   📁 Objects deleted: {self.stats['s3']['objects_deleted']}")
        
        logger.info(f"\n📨 AWS SQS:")
        logger.info(f"   📬 Messages purged: {self.stats['sqs']['messages_purged']}")
        
        logger.info("\n" + "="*60)
        
        if self.dry_run:
            logger.info("🔍 DRY RUN COMPLETE - No data was actually deleted")
        else:
            logger.info("✅ RESET COMPLETE - All test data wiped clean!")
        
        logger.info("="*60 + "\n")


def safety_check(force: bool = False) -> bool:
    """
    Safety prompt to prevent accidental production wipes
    
    Args:
        force: Skip confirmation if True
    
    Returns:
        bool: True if user confirms, False otherwise
    """
    if force:
        logger.warning("⚠️  --force flag used, skipping confirmation")
        return True
    
    print("\n" + "="*60)
    print("🚨 DANGER ZONE: COMPLETE ENVIRONMENT RESET 🚨")
    print("="*60)
    print("\nThis will DELETE ALL DATA from:")
    print("  • PostgreSQL: documents, document_chunks, users tables")
    print("  • Redis: all task:*, result:*, progress:* keys")
    print("  • AWS S3: all uploaded PDFs")
    print("  • AWS SQS: all queued messages")
    print("\n⚠️  THIS OPERATION IS IRREVERSIBLE!")
    print("⚠️  ALL YOUR DATA WILL BE PERMANENTLY LOST!")
    print("="*60 + "\n")
    
    # First confirmation
    response = input("Are you ABSOLUTELY SURE you want to continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n❌ Reset cancelled by user")
        return False
    
    # Second confirmation with specific text
    print("\n⚠️  FINAL WARNING: This cannot be undone!")
    response = input("Type 'DELETE ALL DATA' to confirm: ").strip()
    if response != 'DELETE ALL DATA':
        print("\n❌ Reset cancelled - confirmation text did not match")
        return False
    
    # Optional: ask about users table
    print("\n")
    response = input("Also delete ALL USERS? This will reset authentication (yes/no): ").strip().lower()
    reset_users = (response == 'yes')
    
    print("\n✅ Confirmation received. Starting reset...\n")
    return True, reset_users


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Complete environment reset utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 reset_env.py              # Interactive mode with safety prompts
  python3 reset_env.py --dry-run    # Show what would be deleted
  python3 reset_env.py --force      # Skip confirmation (DANGEROUS!)

⚠️  WARNING: This script is DESTRUCTIVE and IRREVERSIBLE!
⚠️  DO NOT RUN IN PRODUCTION ENVIRONMENTS!
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts (USE WITH EXTREME CAUTION!)'
    )
    
    parser.add_argument(
        '--skip-postgres',
        action='store_true',
        help='Skip PostgreSQL reset'
    )
    
    parser.add_argument(
        '--skip-redis',
        action='store_true',
        help='Skip Redis reset'
    )
    
    parser.add_argument(
        '--skip-s3',
        action='store_true',
        help='Skip S3 reset'
    )
    
    parser.add_argument(
        '--skip-sqs',
        action='store_true',
        help='Skip SQS reset'
    )
    
    args = parser.parse_args()
    
    # Environment check
    logger.info("🔍 Checking environment...")
    try:
        from app.config import settings
        logger.info(f"   📍 Environment: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
        
        # Production safety check
        if 'prod' in settings.postgres_host.lower() or 'production' in settings.postgres_db.lower():
            logger.error("❌ PRODUCTION ENVIRONMENT DETECTED!")
            logger.error("❌ This script is for development/testing only!")
            logger.error("❌ Aborting for safety!")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        sys.exit(1)
    
    # Safety check (unless dry-run or already confirmed)
    reset_users = False
    if not args.dry_run:
        result = safety_check(force=args.force)
        if isinstance(result, tuple):
            confirmed, reset_users = result
        else:
            confirmed = result
            
        if not confirmed:
            sys.exit(0)
    
    # Create reset handler
    reset = EnvironmentReset(dry_run=args.dry_run)
    
    # Track overall success
    all_success = True
    
    # Reset each service
    if not args.skip_postgres:
        success = reset.reset_postgresql(reset_users=reset_users)
        all_success = all_success and success
    
    if not args.skip_redis:
        success = reset.reset_redis()
        all_success = all_success and success
    
    if not args.skip_s3:
        success = reset.reset_s3()
        all_success = all_success and success
    
    if not args.skip_sqs:
        success = reset.reset_sqs()
        all_success = all_success and success
    
    # Print summary
    reset.print_summary()
    
    # Exit with appropriate code
    if all_success:
        logger.info("🎉 Environment reset completed successfully!")
        sys.exit(0)
    else:
        logger.error("⚠️  Some operations failed - check logs above")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Reset cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
