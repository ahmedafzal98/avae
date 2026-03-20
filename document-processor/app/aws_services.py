"""AWS Services Helper - S3 and SQS operations"""
import boto3
import json
import logging
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError
from app.config import settings

logger = logging.getLogger(__name__)


class AWSServices:
    """Centralized AWS service management"""
    
    def __init__(self):
        """Initialize AWS clients"""
        self.s3_client = boto3.client(
            's3',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        
        self.sqs_client = boto3.client(
            'sqs',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
    
    # ============= S3 OPERATIONS =============
    
    def upload_file_to_s3(
        self,
        file_content: bytes,
        s3_key: str,
        content_type: str = "application/pdf"
    ) -> bool:
        """
        Upload file to S3 bucket
        
        Args:
            file_content: File content as bytes
            s3_key: S3 key (path) for the file (e.g., "uploads/task-123.pdf")
            content_type: MIME type of the file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            logger.info(f"✅ Uploaded to S3: {s3_key}")
            return True
        
        except ClientError as e:
            logger.error(f"❌ S3 upload failed for {s3_key}: {e}")
            return False
    
    def download_file_from_s3(self, s3_key: str) -> Optional[bytes]:
        """
        Download file from S3 bucket
        
        Args:
            s3_key: S3 key (path) of the file
        
        Returns:
            bytes: File content if successful, None otherwise
        """
        try:
            response = self.s3_client.get_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key
            )
            file_content = response['Body'].read()
            logger.info(f"✅ Downloaded from S3: {s3_key}")
            return file_content
        
        except ClientError as e:
            logger.error(f"❌ S3 download failed for {s3_key}: {e}")
            return None
    
    def delete_file_from_s3(self, s3_key: str) -> bool:
        """
        Delete file from S3 bucket
        
        Args:
            s3_key: S3 key (path) of the file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key
            )
            logger.info(f"✅ Deleted from S3: {s3_key}")
            return True
        
        except ClientError as e:
            logger.error(f"❌ S3 delete failed for {s3_key}: {e}")
            return False
    
    def check_file_exists_in_s3(self, s3_key: str) -> bool:
        """
        Check if file exists in S3
        
        Args:
            s3_key: S3 key (path) of the file
        
        Returns:
            bool: True if exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key
            )
            return True
        
        except ClientError:
            return False
    
    # ============= SQS OPERATIONS =============
    
    def send_message_to_sqs(
        self,
        message_body: Dict[str, Any],
        message_attributes: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Send message to SQS queue
        
        Args:
            message_body: Dictionary containing message data
            message_attributes: Optional message attributes
        
        Returns:
            str: Message ID if successful, None otherwise
        """
        try:
            # Convert message body to JSON string
            body_json = json.dumps(message_body)
            
            # Prepare message parameters
            message_params = {
                'QueueUrl': settings.effective_sqs_queue_url,
                'MessageBody': body_json
            }
            
            # Add message attributes if provided
            if message_attributes:
                sqs_attributes = {}
                for key, value in message_attributes.items():
                    sqs_attributes[key] = {
                        'StringValue': str(value),
                        'DataType': 'String'
                    }
                message_params['MessageAttributes'] = sqs_attributes
            
            # Send message
            response = self.sqs_client.send_message(**message_params)
            message_id = response['MessageId']
            
            logger.info(f"✅ Message sent to SQS: {message_id}")
            return message_id
        
        except ClientError as e:
            logger.error(f"❌ SQS send failed: {e}")
            return None
    
    def receive_messages_from_sqs(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 20,
        visibility_timeout: int = 900
    ) -> List[Dict[str, Any]]:
        """
        Receive messages from SQS queue (long polling)
        
        Args:
            max_messages: Maximum number of messages to retrieve (1-10)
            wait_time_seconds: Long polling wait time (0-20 seconds)
            visibility_timeout: Time message is invisible after retrieval (seconds)
        
        Returns:
            List of message dictionaries with 'body', 'receipt_handle', 'message_id'
        """
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=settings.effective_sqs_queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout,
                MessageAttributeNames=['All'],
                AttributeNames=['All'],  # Include ApproximateReceiveCount for poison detection
            )
            
            messages = []
            if 'Messages' in response:
                for msg in response['Messages']:
                    # Parse JSON body back to dictionary
                    body_dict = json.loads(msg['Body'])
                    attrs = msg.get('Attributes', {})
                    receive_count = int(attrs.get('ApproximateReceiveCount', 1))
                    
                    messages.append({
                        'body': body_dict,
                        'receipt_handle': msg['ReceiptHandle'],
                        'message_id': msg['MessageId'],
                        'attributes': msg.get('MessageAttributes', {}),
                        'receive_count': receive_count,
                    })
                
                logger.info(f"✅ Received {len(messages)} message(s) from SQS")
            
            return messages
        
        except ClientError as e:
            logger.error(f"❌ SQS receive failed: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse SQS message body: {e}")
            return []
    
    def delete_message_from_sqs(self, receipt_handle: str) -> bool:
        """
        Delete message from SQS queue (acknowledge processing)
        
        Args:
            receipt_handle: Receipt handle from received message
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.sqs_client.delete_message(
                QueueUrl=settings.effective_sqs_queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"✅ Message deleted from SQS")
            return True
        
        except ClientError as e:
            logger.error(f"❌ SQS delete failed: {e}")
            return False
    
    def get_queue_attributes(self) -> Optional[Dict[str, Any]]:
        """
        Get SQS queue attributes (for monitoring)
        
        Returns:
            Dict with queue attributes or None
        """
        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=settings.effective_sqs_queue_url,
                AttributeNames=['All']
            )
            return response.get('Attributes', {})
        
        except ClientError as e:
            logger.error(f"❌ Failed to get queue attributes: {e}")
            return None


# Singleton instance
aws_services = AWSServices()
