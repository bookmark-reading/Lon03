"""
DynamoDB Persistence Layer for Reading Assistant
Handles all DynamoDB operations with async write-behind pattern
"""
import asyncio
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
import json

from models import AudioChunk, Transcription, HelpEvent, ReadingSession
from dynamodb_models import DynamoDBMapper
from dynamodb_config import DynamoDBConfig


class DynamoDBPersistence:
    """Handles all DynamoDB operations for session metadata"""
    
    def __init__(self, table_name: str = None, region: str = None):
        self.table_name = table_name or DynamoDBConfig.TABLE_NAME
        self.region = region or DynamoDBConfig.REGION
        
        # Initialize DynamoDB client
        dynamodb_kwargs = {'region_name': self.region}
        if DynamoDBConfig.ENDPOINT_URL:
            dynamodb_kwargs['endpoint_url'] = DynamoDBConfig.ENDPOINT_URL
        
        self.dynamodb = boto3.resource('dynamodb', **dynamodb_kwargs)
        self.table = self.dynamodb.Table(self.table_name)
        
        # Write queues for batching
        self.chunk_queue: List[AudioChunk] = []
        self.transcription_queue: List[Transcription] = []
        self.write_queue: asyncio.Queue = asyncio.Queue(maxsize=DynamoDBConfig.MAX_QUEUE_SIZE)
        
        # Worker control
        self.workers_running = False
        self.worker_tasks = []
        
        print(f"[DynamoDB] Initialized persistence layer")
        print(f"[DynamoDB] Table: {self.table_name}, Region: {self.region}")
    
    # ==================== Write Operations ====================
    
    async def save_session(self, session: ReadingSession) -> bool:
        """Save session metadata to DynamoDB"""
        try:
            item = DynamoDBMapper.session_to_item(session)
            
            # Async write to avoid blocking
            await self.write_queue.put(('put_item', item))
            
            print(f"[DynamoDB] Queued session: {session.session_id}")
            return True
            
        except Exception as e:
            print(f"[DynamoDB] Error saving session: {e}")
            return False
    
    async def save_audio_chunk(self, chunk: AudioChunk) -> bool:
        """Save audio chunk to DynamoDB"""
        try:
            # Add to batch queue
            self.chunk_queue.append(chunk)
            
            # Flush if batch size reached
            if len(self.chunk_queue) >= DynamoDBConfig.CHUNK_BATCH_SIZE:
                await self.flush_chunk_queue()
            
            return True
            
        except Exception as e:
            print(f"[DynamoDB] Error saving audio chunk: {e}")
            return False
    
    async def save_transcription(self, transcription: Transcription) -> bool:
        """Save transcription to DynamoDB"""
        try:
            # Add to batch queue
            self.transcription_queue.append(transcription)
            
            # Flush if batch size reached
            if len(self.transcription_queue) >= DynamoDBConfig.TRANSCRIPTION_BATCH_SIZE:
                await self.flush_transcription_queue()
            
            return True
            
        except Exception as e:
            print(f"[DynamoDB] Error saving transcription: {e}")
            return False
    
    async def save_help_event(self, help_event: HelpEvent) -> bool:
        """Save help event to DynamoDB (immediate write by default)"""
        try:
            item = DynamoDBMapper.help_event_to_item(help_event)
            
            # Check if immediate write is enabled
            if DynamoDBConfig.IMMEDIATE_WRITE_HELP_EVENTS:
                # Write immediately (synchronous)
                await self._write_item_immediately(item)
                print(f"[DynamoDB] Saved help event immediately: {help_event.event_id}")
            else:
                # Queue for background write
                await self.write_queue.put(('put_item', item))
                print(f"[DynamoDB] Queued help event: {help_event.event_id}")
            
            return True
            
        except Exception as e:
            print(f"[DynamoDB] Error saving help event: {e}")
            return False
    
    async def update_session_metrics(self, session_id: UUID, metrics: dict) -> bool:
        """Update session metrics"""
        try:
            update_expr = "SET Metrics = :metrics, UpdatedAt = :updated"
            expr_values = {
                ':metrics': metrics,
                ':updated': datetime.now().isoformat()
            }
            
            await self.write_queue.put(('update_item', {
                'Key': {
                    'PK': f'SESSION#{session_id}',
                    'SK': 'METADATA'
                },
                'UpdateExpression': update_expr,
                'ExpressionAttributeValues': expr_values
            }))
            
            return True
            
        except Exception as e:
            print(f"[DynamoDB] Error updating metrics: {e}")
            return False
    
    async def end_session(self, session_id: UUID, end_time: datetime) -> bool:
        """Mark session as ended"""
        try:
            update_expr = "SET EndTime = :end_time, IsActive = :active, UpdatedAt = :updated"
            expr_values = {
                ':end_time': end_time.isoformat(),
                ':active': False,
                ':updated': datetime.now().isoformat()
            }
            
            await self.write_queue.put(('update_item', {
                'Key': {
                    'PK': f'SESSION#{session_id}',
                    'SK': 'METADATA'
                },
                'UpdateExpression': update_expr,
                'ExpressionAttributeValues': expr_values
            }))
            
            # Flush any remaining queued items
            await self.flush_all_queues()
            
            print(f"[DynamoDB] Session ended: {session_id}")
            return True
            
        except Exception as e:
            print(f"[DynamoDB] Error ending session: {e}")
            return False
    
    async def save_batch_metrics(self, batch_metrics) -> bool:
        """Save batch metrics to DynamoDB (immediate write by default)"""
        try:
            item = DynamoDBMapper.batch_metrics_to_item(batch_metrics)
            
            if not item:
                return False
            
            # Check if immediate write is enabled
            if DynamoDBConfig.IMMEDIATE_WRITE_BATCH_METRICS:
                # Write immediately (synchronous)
                await self._write_item_immediately(item)
                print(f"[DynamoDB] Saved batch metrics immediately: {batch_metrics.batch_id}")
            else:
                # Queue for background write
                await self.write_queue.put(('put_item', item))
                print(f"[DynamoDB] Queued batch metrics: {batch_metrics.batch_id}")
            
            return True
            
        except Exception as e:
            print(f"[DynamoDB] Error saving batch metrics: {e}")
            return False
    
    async def save_session_summary(self, session_summary) -> bool:
        """Save session summary to DynamoDB (immediate write by default)"""
        try:
            item = DynamoDBMapper.session_summary_to_item(session_summary)
            
            if not item:
                return False
            
            # Check if immediate write is enabled
            if DynamoDBConfig.IMMEDIATE_WRITE_SESSION_SUMMARY:
                # Write immediately (synchronous)
                await self._write_item_immediately(item)
                print(f"[DynamoDB] Saved session summary immediately: {session_summary.session_id}")
            else:
                # Queue for background write
                await self.write_queue.put(('put_item', item))
                print(f"[DynamoDB] Queued session summary: {session_summary.session_id}")
            
            return True
            
        except Exception as e:
            print(f"[DynamoDB] Error saving session summary: {e}")
            return False
    
    # ==================== Batch Operations ====================
    
    async def flush_chunk_queue(self):
        """Flush audio chunk queue to DynamoDB"""
        if not self.chunk_queue:
            return
        
        try:
            items = [DynamoDBMapper.audio_chunk_to_item(chunk) for chunk in self.chunk_queue]
            await self.batch_write_items(items)
            
            print(f"[DynamoDB] Flushed {len(self.chunk_queue)} audio chunks")
            self.chunk_queue.clear()
            
        except Exception as e:
            print(f"[DynamoDB] Error flushing chunk queue: {e}")
    
    async def flush_transcription_queue(self):
        """Flush transcription queue to DynamoDB"""
        if not self.transcription_queue:
            return
        
        try:
            items = [DynamoDBMapper.transcription_to_item(trans) for trans in self.transcription_queue]
            await self.batch_write_items(items)
            
            print(f"[DynamoDB] Flushed {len(self.transcription_queue)} transcriptions")
            self.transcription_queue.clear()
            
        except Exception as e:
            print(f"[DynamoDB] Error flushing transcription queue: {e}")
    
    async def flush_all_queues(self):
        """Flush all queues"""
        await self.flush_chunk_queue()
        await self.flush_transcription_queue()
    
    async def batch_write_items(self, items: List[Dict]):
        """Batch write items to DynamoDB"""
        if not items:
            return
        
        # DynamoDB batch write limit is 25 items
        batch_size = DynamoDBConfig.BATCH_SIZE
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            try:
                with self.table.batch_writer() as writer:
                    for item in batch:
                        writer.put_item(Item=item)
                
            except ClientError as e:
                print(f"[DynamoDB] Batch write error: {e}")
                # Retry individual items
                for item in batch:
                    try:
                        self.table.put_item(Item=item)
                    except Exception as retry_error:
                        print(f"[DynamoDB] Failed to write item: {retry_error}")
    
    # ==================== Read Operations ====================
    
    async def get_session_metadata(self, session_id: UUID) -> Optional[Dict]:
        """Get session metadata only"""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'SESSION#{session_id}',
                    'SK': 'METADATA'
                }
            )
            
            if 'Item' in response:
                return DynamoDBMapper.item_to_session_metadata(response['Item'])
            
            return None
            
        except Exception as e:
            print(f"[DynamoDB] Error getting session metadata: {e}")
            return None
    
    async def get_audio_chunks(self, session_id: UUID) -> List[AudioChunk]:
        """Get all audio chunks for a session"""
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'SESSION#{session_id}',
                    ':sk': 'CHUNK#'
                }
            )
            
            chunks = [DynamoDBMapper.item_to_audio_chunk(item) for item in response.get('Items', [])]
            return sorted(chunks, key=lambda c: c.sequence_number)
            
        except Exception as e:
            print(f"[DynamoDB] Error getting audio chunks: {e}")
            return []
    
    async def get_transcriptions(self, session_id: UUID) -> List[Transcription]:
        """Get all transcriptions for a session"""
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'SESSION#{session_id}',
                    ':sk': 'TRANS#'
                }
            )
            
            transcriptions = [DynamoDBMapper.item_to_transcription(item) for item in response.get('Items', [])]
            return sorted(transcriptions, key=lambda t: t.created_at)
            
        except Exception as e:
            print(f"[DynamoDB] Error getting transcriptions: {e}")
            return []
    
    async def get_help_events(self, session_id: UUID) -> List[HelpEvent]:
        """Get all help events for a session"""
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'SESSION#{session_id}',
                    ':sk': 'HELP#'
                }
            )
            
            help_events = [DynamoDBMapper.item_to_help_event(item) for item in response.get('Items', [])]
            return sorted(help_events, key=lambda h: h.response_timestamp)
            
        except Exception as e:
            print(f"[DynamoDB] Error getting help events: {e}")
            return []
    
    async def get_student_sessions(self, student_id: str, limit: int = 50) -> List[Dict]:
        """Get all sessions for a student"""
        try:
            response = self.table.query(
                IndexName='GSI2',
                KeyConditionExpression='GSI2PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'STUDENT#{student_id}'
                },
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            
            sessions = []
            for item in response.get('Items', []):
                if item.get('Type') == 'SESSION':
                    sessions.append(DynamoDBMapper.item_to_session_metadata(item))
            
            return sessions
            
        except Exception as e:
            print(f"[DynamoDB] Error getting student sessions: {e}")
            return []
    
    async def get_sessions_by_date(self, date: str, limit: int = 100) -> List[Dict]:
        """Get all sessions for a specific date (YYYY-MM-DD)"""
        try:
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk AND begins_with(GSI1SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': 'SESSION',
                    ':sk': f'DATE#{date}'
                },
                Limit=limit
            )
            
            sessions = [DynamoDBMapper.item_to_session_metadata(item) for item in response.get('Items', [])]
            return sessions
            
        except Exception as e:
            print(f"[DynamoDB] Error getting sessions by date: {e}")
            return []
    
    async def get_batch_metrics(self, session_id: UUID) -> List[Dict]:
        """Get all batch metrics for a session"""
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'SESSION#{session_id}',
                    ':sk': 'BATCH#'
                }
            )
            
            batch_metrics = []
            for item in response.get('Items', []):
                batch_metrics.append({
                    'batch_id': item['BatchId'],
                    'session_id': item['SessionId'],
                    'start_time': item['StartTime'],
                    'end_time': item['EndTime'],
                    'duration_seconds': item['DurationSeconds'],
                    'word_count': item['WordCount'],
                    'words_per_minute': item['WordsPerMinute'],
                    'average_confidence': item['AverageConfidence'],
                    'miscue_counts': item['MiscueCounts'],
                    'miscue_events': item.get('MiscueEvents', []),
                    'transcriptions': item.get('Transcriptions', []),
                    'expected_text': item.get('ExpectedText'),
                    'accuracy_percentage': item.get('AccuracyPercentage')
                })
            
            return sorted(batch_metrics, key=lambda b: b['start_time'])
            
        except Exception as e:
            print(f"[DynamoDB] Error getting batch metrics: {e}")
            return []
    
    async def get_session_summary(self, session_id: UUID) -> Optional[Dict]:
        """Get session summary"""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'SESSION#{session_id}',
                    'SK': 'SUMMARY'
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                return {
                    'session_id': item['SessionId'],
                    'start_time': item['StartTime'],
                    'end_time': item['EndTime'],
                    'total_duration_minutes': item['TotalDurationMinutes'],
                    'total_words': item['TotalWords'],
                    'average_wpm': item['AverageWpm'],
                    'overall_accuracy': item.get('OverallAccuracy'),
                    'average_confidence': item['AverageConfidence'],
                    'total_miscue_counts': item['TotalMiscueCounts'],
                    'all_miscue_events': item.get('AllMiscueEvents', []),
                    'full_transcript': item.get('FullTranscript', ''),
                    'expected_passage': item.get('ExpectedPassage'),
                    'insights': item.get('Insights', {}),
                    'batch_metrics_count': item.get('BatchMetricsCount', 0)
                }
            
            return None
            
        except Exception as e:
            print(f"[DynamoDB] Error getting session summary: {e}")
            return None
    
    async def get_complete_session_data(self, session_id: UUID) -> Dict:
        """Get complete session data including metadata, transcriptions, help events, batch metrics, and summary"""
        try:
            session_metadata = await self.get_session_metadata(session_id)
            transcriptions = await self.get_transcriptions(session_id)
            help_events = await self.get_help_events(session_id)
            batch_metrics = await self.get_batch_metrics(session_id)
            session_summary = await self.get_session_summary(session_id)
            
            return {
                'session_metadata': session_metadata,
                'transcriptions': [t.to_dict() for t in transcriptions],
                'help_events': [h.to_dict() for h in help_events],
                'batch_metrics': batch_metrics,
                'session_summary': session_summary
            }
            
        except Exception as e:
            print(f"[DynamoDB] Error getting complete session data: {e}")
            return {}
    
    # ==================== Background Workers ====================
    
    async def start_write_worker(self):
        """Start background write worker"""
        self.workers_running = True
        
        print(f"[DynamoDB] Starting {DynamoDBConfig.WORKER_COUNT} write workers")
        
        for i in range(DynamoDBConfig.WORKER_COUNT):
            task = asyncio.create_task(self._write_worker(i))
            self.worker_tasks.append(task)
        
        # Start periodic flush task
        flush_task = asyncio.create_task(self._periodic_flush())
        self.worker_tasks.append(flush_task)
    
    async def stop_workers(self):
        """Stop all background workers"""
        self.workers_running = False
        
        # Flush remaining items
        await self.flush_all_queues()
        
        # Cancel worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        print("[DynamoDB] Workers stopped")
    
    async def _write_worker(self, worker_id: int):
        """Background worker for processing write queue"""
        print(f"[DynamoDB] Write worker {worker_id} started")
        
        while self.workers_running:
            try:
                # Get item from queue with timeout
                operation, data = await asyncio.wait_for(
                    self.write_queue.get(),
                    timeout=1.0
                )
                
                # Execute operation
                if operation == 'put_item':
                    self.table.put_item(Item=data)
                elif operation == 'update_item':
                    self.table.update_item(**data)
                
                self.write_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[DynamoDB] Worker {worker_id} error: {e}")
    
    async def _periodic_flush(self):
        """Periodically flush batch queues"""
        while self.workers_running:
            await asyncio.sleep(DynamoDBConfig.BATCH_INTERVAL_SECONDS)
            await self.flush_all_queues()
    
    # ==================== Utility Methods ====================
    
    async def _write_item_immediately(self, item: Dict):
        """Write item to DynamoDB immediately (synchronous)"""
        try:
            # Use asyncio to run the synchronous boto3 call
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.table.put_item(Item=item))
        except Exception as e:
            print(f"[DynamoDB] Immediate write error: {e}")
            raise
    
    async def create_student_index(self, student_id: str, session_id: UUID, start_time: datetime):
        """Create index entry for student lookup"""
        try:
            item = DynamoDBMapper.create_student_index_item(student_id, session_id, start_time)
            await self.write_queue.put(('put_item', item))
            
        except Exception as e:
            print(f"[DynamoDB] Error creating student index: {e}")
    
    def get_queue_depth(self) -> Dict[str, int]:
        """Get current queue depths"""
        return {
            'write_queue': self.write_queue.qsize(),
            'chunk_queue': len(self.chunk_queue),
            'transcription_queue': len(self.transcription_queue)
        }
