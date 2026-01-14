"""
DynamoDB Configuration for Reading Assistant
"""
import os
from typing import Optional


class DynamoDBConfig:
    """Configuration for DynamoDB persistence"""
    
    # Table Configuration
    TABLE_NAME: str = os.getenv('DYNAMODB_TABLE_NAME', 'reading_sessions')
    REGION: str = os.getenv('DYNAMODB_REGION', 'us-east-1')
    ENDPOINT_URL: Optional[str] = os.getenv('DYNAMODB_ENDPOINT_URL')  # For local testing
    
    # Feature Flag
    ENABLED: bool = os.getenv('ENABLE_DYNAMODB_PERSISTENCE', 'false').lower() == 'true'
    
    # Write Settings
    BATCH_SIZE: int = int(os.getenv('DYNAMODB_BATCH_SIZE', '25'))
    BATCH_INTERVAL_SECONDS: int = int(os.getenv('DYNAMODB_BATCH_INTERVAL', '5'))
    CHUNK_BATCH_SIZE: int = int(os.getenv('DYNAMODB_CHUNK_BATCH_SIZE', '10'))
    TRANSCRIPTION_BATCH_SIZE: int = int(os.getenv('DYNAMODB_TRANSCRIPTION_BATCH_SIZE', '5'))
    
    # Immediate Write Settings
    IMMEDIATE_WRITE_BATCH_METRICS: bool = os.getenv('DYNAMODB_IMMEDIATE_BATCH_METRICS', 'true').lower() == 'true'
    IMMEDIATE_WRITE_SESSION_SUMMARY: bool = os.getenv('DYNAMODB_IMMEDIATE_SESSION_SUMMARY', 'true').lower() == 'true'
    IMMEDIATE_WRITE_HELP_EVENTS: bool = os.getenv('DYNAMODB_IMMEDIATE_HELP_EVENTS', 'true').lower() == 'true'
    
    # TTL Settings (30 days default)
    TTL_DAYS: int = int(os.getenv('DYNAMODB_TTL_DAYS', '30'))
    
    # S3 Settings (Optional)
    S3_BUCKET: str = os.getenv('S3_AUDIO_BUCKET', 'bookmark-reading-charity-audio')
    STORE_AUDIO_IN_S3: bool = os.getenv('STORE_AUDIO_IN_S3', 'false').lower() == 'true'
    
    # Retry Settings
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 1
    
    # Queue Settings
    MAX_QUEUE_SIZE: int = 1000
    WORKER_COUNT: int = 2
    
    @classmethod
    def get_ttl_timestamp(cls) -> int:
        """Get TTL timestamp (current time + TTL_DAYS)"""
        from datetime import datetime, timedelta
        expiry = datetime.now() + timedelta(days=cls.TTL_DAYS)
        return int(expiry.timestamp())
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if DynamoDB persistence is enabled"""
        return cls.ENABLED
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Get configuration summary for logging"""
        return {
            'table_name': cls.TABLE_NAME,
            'region': cls.REGION,
            'enabled': cls.ENABLED,
            'batch_size': cls.BATCH_SIZE,
            'ttl_days': cls.TTL_DAYS,
            's3_enabled': cls.STORE_AUDIO_IN_S3,
            'immediate_batch_metrics': cls.IMMEDIATE_WRITE_BATCH_METRICS,
            'immediate_session_summary': cls.IMMEDIATE_WRITE_SESSION_SUMMARY,
            'immediate_help_events': cls.IMMEDIATE_WRITE_HELP_EVENTS
        }
