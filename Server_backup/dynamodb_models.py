"""
DynamoDB data models and mappers
Converts domain models to/from DynamoDB items
"""
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID
from models import (
    AudioChunk,
    Transcription,
    HelpEvent,
    WordTimestamp,
    ReadingSession,
    SessionMetrics
)
from dynamodb_config import DynamoDBConfig

# Import analysis models
try:
    from analysis.analysis_models import BatchMetrics, SessionSummary, MiscueEvent
    ANALYSIS_MODELS_AVAILABLE = True
except ImportError:
    ANALYSIS_MODELS_AVAILABLE = False


class DynamoDBMapper:
    """Maps domain models to DynamoDB items and vice versa"""
    
    @staticmethod
    def session_to_item(session: ReadingSession) -> Dict[str, Any]:
        """Convert ReadingSession to DynamoDB item"""
        item = {
            'PK': f'SESSION#{session.session_id}',
            'SK': 'METADATA',
            'Type': 'SESSION',
            'SessionId': str(session.session_id),
            'ClientId': session.client_id,
            'StartTime': session.start_time.isoformat(),
            'EndTime': session.end_time.isoformat() if session.end_time else None,
            'TotalDurationMs': session.total_duration_ms,
            'IsActive': session.is_active,
            'Metrics': {
                'TotalWords': session.metrics.total_words,
                'ReadingSpeedWpm': session.metrics.reading_speed_wpm,
                'PauseCount': session.metrics.pause_count,
                'TotalPauseDurationMs': session.metrics.total_pause_duration_ms,
                'HelpRequestCount': session.metrics.help_request_count,
                'AverageConfidence': session.metrics.average_confidence,
                'TotalReadingTimeMs': session.metrics.total_reading_time_ms
            },
            'AudioChunksCount': len(session.audio_chunks),
            'TranscriptionsCount': len(session.transcriptions),
            'HelpEventsCount': len(session.help_events),
            'GSI1PK': 'SESSION',
            'GSI1SK': f"DATE#{session.start_time.strftime('%Y-%m-%d')}#{session.start_time.isoformat()}",
            'GSI2PK': f'CLIENT#{session.client_id}',
            'GSI2SK': f"DATE#{session.start_time.strftime('%Y-%m-%d')}#{session.start_time.isoformat()}",
            'CreatedAt': session.start_time.isoformat(),
            'UpdatedAt': datetime.now().isoformat(),
            'TTL': DynamoDBConfig.get_ttl_timestamp()
        }
        return item
    
    @staticmethod
    def audio_chunk_to_item(chunk: AudioChunk) -> Dict[str, Any]:
        """Convert AudioChunk to DynamoDB item"""
        item = {
            'PK': f'SESSION#{chunk.session_id}',
            'SK': f"CHUNK#{chunk.received_timestamp.isoformat()}#{chunk.sequence_number:04d}",
            'Type': 'AUDIO_CHUNK',
            'ChunkId': str(chunk.chunk_id),
            'SessionId': str(chunk.session_id),
            'ClientId': chunk.client_id,
            'SequenceNumber': chunk.sequence_number,
            'ReceivedTimestamp': chunk.received_timestamp.isoformat(),
            'SessionOffsetMs': chunk.session_offset_ms,
            'DurationMs': chunk.duration_ms,
            'SampleRate': chunk.sample_rate,
            'Encoding': chunk.encoding,
            'SizeBytes': chunk.size_bytes,
            'CreatedAt': chunk.received_timestamp.isoformat(),
            'TTL': DynamoDBConfig.get_ttl_timestamp()
        }
        
        # Optional: Add S3 key if audio is stored
        if chunk.audio_data and DynamoDBConfig.STORE_AUDIO_IN_S3:
            item['AudioDataS3Key'] = f"sessions/{chunk.session_id}/chunks/{chunk.sequence_number:04d}.{chunk.encoding}"
        
        return item
    
    @staticmethod
    def transcription_to_item(transcription: Transcription) -> Dict[str, Any]:
        """Convert Transcription to DynamoDB item"""
        item = {
            'PK': f'SESSION#{transcription.session_id}',
            'SK': f"TRANS#{transcription.created_at.isoformat()}#{transcription.transcription_id}",
            'Type': 'TRANSCRIPTION',
            'TranscriptionId': str(transcription.transcription_id),
            'SessionId': str(transcription.session_id),
            'AudioChunkIds': [str(cid) for cid in transcription.audio_chunk_ids],
            'Text': transcription.text,
            'StartTimeMs': transcription.start_time_ms,
            'EndTimeMs': transcription.end_time_ms,
            'SessionOffsetMs': transcription.session_offset_ms,
            'Confidence': transcription.confidence,
            'IsFinal': transcription.is_final,
            'WordTimestamps': [
                {
                    'Word': wt.word,
                    'StartTimeMs': wt.start_time_ms,
                    'EndTimeMs': wt.end_time_ms,
                    'Confidence': wt.confidence
                }
                for wt in transcription.word_timestamps
            ],
            'CreatedAt': transcription.created_at.isoformat(),
            'TTL': DynamoDBConfig.get_ttl_timestamp()
        }
        return item
    
    @staticmethod
    def help_event_to_item(help_event: HelpEvent) -> Dict[str, Any]:
        """Convert HelpEvent to DynamoDB item"""
        item = {
            'PK': f'SESSION#{help_event.session_id}',
            'SK': f"HELP#{help_event.response_timestamp.isoformat()}#{help_event.event_id}",
            'Type': 'HELP_EVENT',
            'EventId': str(help_event.event_id),
            'SessionId': str(help_event.session_id),
            'SessionTimeOffsetMs': help_event.session_time_offset_ms,
            'TriggerTranscriptions': help_event.trigger_transcriptions,
            'TriggerTimestamps': help_event.trigger_timestamps,
            'AccumulationDurationMs': help_event.accumulation_duration_ms,
            'AudioSegmentIds': [str(sid) for sid in help_event.audio_segment_ids],
            'HelpMessage': help_event.help_message,
            'Confidence': help_event.confidence,
            'Reason': help_event.reason,
            'ResponseTimestamp': help_event.response_timestamp.isoformat(),
            'GSI1PK': 'HELP_EVENT',
            'GSI1SK': f"DATE#{help_event.response_timestamp.strftime('%Y-%m-%d')}#{help_event.response_timestamp.isoformat()}",
            'CreatedAt': help_event.response_timestamp.isoformat(),
            'TTL': DynamoDBConfig.get_ttl_timestamp()
        }
        
        # Optional: Add S3 key if audio response is stored
        if help_event.audio_response and DynamoDBConfig.STORE_AUDIO_IN_S3:
            item['AudioResponseS3Key'] = f"sessions/{help_event.session_id}/help/{help_event.event_id}.mp3"
        
        return item
    
    @staticmethod
    def item_to_session_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB item to session metadata dict"""
        return {
            'session_id': item['SessionId'],
            'client_id': item['ClientId'],
            'start_time': item['StartTime'],
            'end_time': item.get('EndTime'),
            'total_duration_ms': item['TotalDurationMs'],
            'is_active': item['IsActive'],
            'metrics': item['Metrics'],
            'audio_chunks_count': item['AudioChunksCount'],
            'transcriptions_count': item['TranscriptionsCount'],
            'help_events_count': item['HelpEventsCount']
        }
    
    @staticmethod
    def item_to_audio_chunk(item: Dict[str, Any]) -> AudioChunk:
        """Convert DynamoDB item to AudioChunk"""
        return AudioChunk(
            chunk_id=UUID(item['ChunkId']),
            client_id=item['ClientId'],
            session_id=UUID(item['SessionId']),
            sequence_number=item['SequenceNumber'],
            received_timestamp=datetime.fromisoformat(item['ReceivedTimestamp']),
            session_offset_ms=item['SessionOffsetMs'],
            duration_ms=item['DurationMs'],
            sample_rate=item['SampleRate'],
            encoding=item['Encoding'],
            size_bytes=item['SizeBytes'],
            audio_data=None  # Not stored in DynamoDB
        )
    
    @staticmethod
    def item_to_transcription(item: Dict[str, Any]) -> Transcription:
        """Convert DynamoDB item to Transcription"""
        word_timestamps = [
            WordTimestamp(
                word=wt['Word'],
                start_time_ms=wt['StartTimeMs'],
                end_time_ms=wt['EndTimeMs'],
                confidence=wt['Confidence']
            )
            for wt in item.get('WordTimestamps', [])
        ]
        
        return Transcription(
            transcription_id=UUID(item['TranscriptionId']),
            session_id=UUID(item['SessionId']),
            audio_chunk_ids=[UUID(cid) for cid in item['AudioChunkIds']],
            text=item['Text'],
            start_time_ms=item['StartTimeMs'],
            end_time_ms=item['EndTimeMs'],
            session_offset_ms=item['SessionOffsetMs'],
            confidence=item['Confidence'],
            is_final=item['IsFinal'],
            word_timestamps=word_timestamps,
            created_at=datetime.fromisoformat(item['CreatedAt'])
        )
    
    @staticmethod
    def item_to_help_event(item: Dict[str, Any]) -> HelpEvent:
        """Convert DynamoDB item to HelpEvent"""
        return HelpEvent(
            event_id=UUID(item['EventId']),
            session_id=UUID(item['SessionId']),
            session_time_offset_ms=item['SessionTimeOffsetMs'],
            trigger_transcriptions=item['TriggerTranscriptions'],
            trigger_timestamps=item.get('TriggerTimestamps', []),
            accumulation_duration_ms=item.get('AccumulationDurationMs', 0),
            audio_segment_ids=[UUID(sid) for sid in item['AudioSegmentIds']],
            help_message=item['HelpMessage'],
            audio_response=None,  # Not stored in DynamoDB (use S3)
            response_timestamp=datetime.fromisoformat(item['ResponseTimestamp']),
            confidence=item['Confidence'],
            reason=item['Reason']
        )
    
    @staticmethod
    def create_student_index_item(student_id: str, session_id: UUID, start_time: datetime) -> Dict[str, Any]:
        """Create index item for student lookup"""
        return {
            'PK': f'STUDENT#{student_id}',
            'SK': f"SESSION#{start_time.isoformat()}#{session_id}",
            'Type': 'INDEX',
            'StudentId': student_id,
            'SessionId': str(session_id),
            'StartTime': start_time.isoformat(),
            'GSI2PK': f'STUDENT#{student_id}',
            'GSI2SK': f"DATE#{start_time.strftime('%Y-%m-%d')}#{start_time.isoformat()}",
            'TTL': DynamoDBConfig.get_ttl_timestamp()
        }
    
    @staticmethod
    def batch_metrics_to_item(batch_metrics) -> Dict[str, Any]:
        """Convert BatchMetrics to DynamoDB item"""
        if not ANALYSIS_MODELS_AVAILABLE:
            return {}
        
        item = {
            'PK': f'SESSION#{batch_metrics.session_id}',
            'SK': f"BATCH#{batch_metrics.start_time.isoformat()}#{batch_metrics.batch_id}",
            'Type': 'BATCH_METRICS',
            'BatchId': str(batch_metrics.batch_id),
            'SessionId': str(batch_metrics.session_id),
            'StartTime': batch_metrics.start_time.isoformat(),
            'EndTime': batch_metrics.end_time.isoformat(),
            'DurationSeconds': (batch_metrics.end_time - batch_metrics.start_time).total_seconds(),
            'WordCount': batch_metrics.word_count,
            'WordsPerMinute': batch_metrics.words_per_minute,
            'AverageConfidence': batch_metrics.average_confidence,
            'MiscueCounts': {
                'Omissions': batch_metrics.omissions,
                'Insertions': batch_metrics.insertions,
                'Substitutions': batch_metrics.substitutions,
                'Repetitions': batch_metrics.repetitions,
                'SelfCorrections': batch_metrics.self_corrections,
                'Hesitations': batch_metrics.hesitations,
                'Total': (batch_metrics.omissions + batch_metrics.insertions + 
                         batch_metrics.substitutions + batch_metrics.repetitions +
                         batch_metrics.self_corrections + batch_metrics.hesitations)
            },
            'MiscueEvents': [
                {
                    'MiscueType': event.miscue_type.value,
                    'ExpectedWord': event.expected_word,
                    'ActualWord': event.actual_word,
                    'Position': event.position,
                    'TimestampMs': event.timestamp_ms
                }
                for event in batch_metrics.miscue_events
            ],
            'Transcriptions': batch_metrics.transcriptions,
            'ExpectedText': batch_metrics.expected_text,
            'AccuracyPercentage': batch_metrics.accuracy_percentage,
            'GSI1PK': 'BATCH_METRICS',
            'GSI1SK': f"DATE#{batch_metrics.start_time.strftime('%Y-%m-%d')}#{batch_metrics.start_time.isoformat()}",
            'CreatedAt': batch_metrics.start_time.isoformat(),
            'TTL': DynamoDBConfig.get_ttl_timestamp()
        }
        return item
    
    @staticmethod
    def session_summary_to_item(session_summary) -> Dict[str, Any]:
        """Convert SessionSummary to DynamoDB item"""
        if not ANALYSIS_MODELS_AVAILABLE:
            return {}
        
        item = {
            'PK': f'SESSION#{session_summary.session_id}',
            'SK': 'SUMMARY',
            'Type': 'SESSION_SUMMARY',
            'SessionId': str(session_summary.session_id),
            'StartTime': session_summary.start_time.isoformat(),
            'EndTime': session_summary.end_time.isoformat(),
            'TotalDurationMinutes': session_summary.total_reading_time_minutes,
            'TotalWords': session_summary.total_words,
            'AverageWpm': session_summary.average_wpm,
            'OverallAccuracy': session_summary.overall_accuracy,
            'AverageConfidence': session_summary.average_confidence,
            'TotalMiscueCounts': {
                'Omissions': session_summary.total_omissions,
                'Insertions': session_summary.total_insertions,
                'Substitutions': session_summary.total_substitutions,
                'Repetitions': session_summary.total_repetitions,
                'SelfCorrections': session_summary.total_self_corrections,
                'Hesitations': session_summary.total_hesitations,
                'Total': (session_summary.total_omissions + session_summary.total_insertions +
                         session_summary.total_substitutions + session_summary.total_repetitions +
                         session_summary.total_self_corrections + session_summary.total_hesitations)
            },
            'AllMiscueEvents': [
                {
                    'MiscueType': event.miscue_type.value,
                    'ExpectedWord': event.expected_word,
                    'ActualWord': event.actual_word,
                    'Position': event.position,
                    'TimestampMs': event.timestamp_ms
                }
                for event in session_summary.all_miscue_events
            ],
            'FullTranscript': session_summary.full_transcript,
            'ExpectedPassage': session_summary.expected_passage,
            'Insights': session_summary.insights,
            'BatchMetricsCount': len(session_summary.batch_metrics),
            'GSI1PK': 'SESSION_SUMMARY',
            'GSI1SK': f"DATE#{session_summary.start_time.strftime('%Y-%m-%d')}#{session_summary.start_time.isoformat()}",
            'CreatedAt': session_summary.end_time.isoformat(),
            'UpdatedAt': datetime.now().isoformat(),
            'TTL': DynamoDBConfig.get_ttl_timestamp()
        }
        return item
