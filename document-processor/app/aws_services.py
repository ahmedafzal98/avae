"""AWS Services Helper - S3 and SQS operations (with local filesystem fallback for dev)."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from app.dependencies import redis_client

logger = logging.getLogger(__name__)

LOCAL_SQS_REDIS_KEY = "avae:local_sqs"


class AWSServices:
    """Centralized AWS service management"""

    def __init__(self):
        """Initialize AWS clients (skipped in local storage mode)."""
        self._s3_client = None
        self._sqs_client = None
        if not settings.is_local_storage_mode():
            self._s3_client = boto3.client(
                "s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            self._sqs_client = boto3.client(
                "sqs",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
        else:
            logger.info(
                "📁 Local storage mode: files under %s, queue in Redis (%s)",
                settings.storage_path,
                LOCAL_SQS_REDIS_KEY,
            )

    @property
    def s3_client(self):
        return self._s3_client

    @property
    def sqs_client(self):
        return self._sqs_client

    def _local_file_path(self, s3_key: str) -> Path:
        return Path(settings.storage_path) / s3_key

    # ============= S3 OPERATIONS =============

    def upload_file_to_s3(
        self,
        file_content: bytes,
        s3_key: str,
        content_type: str = "application/pdf",
    ) -> bool:
        if settings.is_local_storage_mode():
            try:
                path = self._local_file_path(s3_key)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(file_content)
                logger.info("✅ Saved locally: %s", path)
                return True
            except OSError as e:
                logger.error("❌ Local save failed for %s: %s", s3_key, e)
                return False

        try:
            self.s3_client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
            )
            logger.info("✅ Uploaded to S3: %s", s3_key)
            return True
        except ClientError as e:
            logger.error("❌ S3 upload failed for %s: %s", s3_key, e)
            return False

    def download_file_from_s3(self, s3_key: str) -> Optional[bytes]:
        if settings.is_local_storage_mode():
            path = self._local_file_path(s3_key)
            if not path.is_file():
                logger.error("❌ Local file not found: %s", path)
                return None
            logger.info("✅ Read locally: %s", path)
            return path.read_bytes()

        try:
            response = self.s3_client.get_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
            )
            file_content = response["Body"].read()
            logger.info("✅ Downloaded from S3: %s", s3_key)
            return file_content
        except ClientError as e:
            logger.error("❌ S3 download failed for %s: %s", s3_key, e)
            return None

    def delete_file_from_s3(self, s3_key: str) -> bool:
        if settings.is_local_storage_mode():
            path = self._local_file_path(s3_key)
            try:
                if path.is_file():
                    path.unlink()
                logger.info("✅ Deleted locally: %s", path)
                return True
            except OSError as e:
                logger.error("❌ Local delete failed for %s: %s", s3_key, e)
                return False

        try:
            self.s3_client.delete_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
            )
            logger.info("✅ Deleted from S3: %s", s3_key)
            return True
        except ClientError as e:
            logger.error("❌ S3 delete failed for %s: %s", s3_key, e)
            return False

    def check_file_exists_in_s3(self, s3_key: str) -> bool:
        if settings.is_local_storage_mode():
            return self._local_file_path(s3_key).is_file()

        try:
            self.s3_client.head_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
            )
            return True
        except ClientError:
            return False

    # ============= SQS OPERATIONS =============

    def send_message_to_sqs(
        self,
        message_body: Dict[str, Any],
        message_attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if settings.is_local_storage_mode():
            try:
                body_json = json.dumps(message_body)
                redis_client.lpush(LOCAL_SQS_REDIS_KEY, body_json)
                task_id = message_body.get("task_id", "unknown")
                message_id = f"local-{task_id}"
                logger.info("✅ Queued locally (Redis): %s", message_id)
                return message_id
            except Exception as e:
                logger.error("❌ Local queue send failed: %s", e)
                return None

        try:
            body_json = json.dumps(message_body)
            message_params = {
                "QueueUrl": settings.effective_sqs_queue_url,
                "MessageBody": body_json,
            }
            if message_attributes:
                sqs_attributes = {}
                for key, value in message_attributes.items():
                    sqs_attributes[key] = {
                        "StringValue": str(value),
                        "DataType": "String",
                    }
                message_params["MessageAttributes"] = sqs_attributes

            response = self.sqs_client.send_message(**message_params)
            message_id = response["MessageId"]
            logger.info("✅ Message sent to SQS: %s", message_id)
            return message_id
        except ClientError as e:
            logger.error("❌ SQS send failed: %s", e)
            return None

    def receive_messages_from_sqs(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 20,
        visibility_timeout: int = 900,
    ) -> List[Dict[str, Any]]:
        if settings.is_local_storage_mode():
            messages = []
            timeout = max(1, min(wait_time_seconds, 20))
            for _ in range(max_messages):
                result = redis_client.brpop(LOCAL_SQS_REDIS_KEY, timeout=timeout)
                if not result:
                    break
                _, body_json = result
                try:
                    body_dict = json.loads(body_json)
                    messages.append(
                        {
                            "body": body_dict,
                            "receipt_handle": "local",
                            "message_id": f"local-{body_dict.get('task_id', '')}",
                            "attributes": {},
                            "receive_count": 1,
                        }
                    )
                except json.JSONDecodeError as e:
                    logger.error("❌ Failed to parse local queue message: %s", e)
            if messages:
                logger.info("✅ Received %d message(s) from local queue", len(messages))
            return messages

        try:
            response = self.sqs_client.receive_message(
                QueueUrl=settings.effective_sqs_queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout,
                MessageAttributeNames=["All"],
                AttributeNames=["All"],
            )

            messages = []
            if "Messages" in response:
                for msg in response["Messages"]:
                    body_dict = json.loads(msg["Body"])
                    attrs = msg.get("Attributes", {})
                    receive_count = int(attrs.get("ApproximateReceiveCount", 1))

                    messages.append(
                        {
                            "body": body_dict,
                            "receipt_handle": msg["ReceiptHandle"],
                            "message_id": msg["MessageId"],
                            "attributes": msg.get("MessageAttributes", {}),
                            "receive_count": receive_count,
                        }
                    )

                logger.info("✅ Received %d message(s) from SQS", len(messages))

            return messages
        except ClientError as e:
            logger.error("❌ SQS receive failed: %s", e)
            return []
        except json.JSONDecodeError as e:
            logger.error("❌ Failed to parse SQS message body: %s", e)
            return []

    def delete_message_from_sqs(self, receipt_handle: str) -> bool:
        if settings.is_local_storage_mode():
            return True

        try:
            self.sqs_client.delete_message(
                QueueUrl=settings.effective_sqs_queue_url,
                ReceiptHandle=receipt_handle,
            )
            logger.info("✅ Message deleted from SQS")
            return True
        except ClientError as e:
            logger.error("❌ SQS delete failed: %s", e)
            return False

    def get_queue_attributes(self) -> Optional[Dict[str, Any]]:
        if settings.is_local_storage_mode():
            try:
                depth = redis_client.llen(LOCAL_SQS_REDIS_KEY)
                return {"ApproximateNumberOfMessages": str(depth)}
            except Exception as e:
                logger.error("❌ Failed to get local queue depth: %s", e)
                return None

        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=settings.effective_sqs_queue_url,
                AttributeNames=["All"],
            )
            return response.get("Attributes", {})
        except ClientError as e:
            logger.error("❌ Failed to get queue attributes: %s", e)
            return None


# Singleton instance
aws_services = AWSServices()
