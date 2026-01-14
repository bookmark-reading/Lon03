"""
Data models for audio timeline metadata and transcription association
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4


@dataclass
class WordTimestamp:
    """Individual word timing information"""
    word: str
    start_time_ms: int
    end_time_ms: int
    confidence: float


@dataclass
class AudioChunk:
    """Metadata for a single audio chunk"""
    chunk_id: UUID
    client_id: str
    session_id: UUID
    sequence_number: int
    received_timestamp: datetime
    session_offset_ms: int
    duration_ms: int
    sample_rate: int
    encoding: str
    size_bytes: int
    audio_data: Optional[bytes] = None  # Optional to save memory
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'chunk_id': str(self.chunk_id),
            'client_id': self.client_id,
            'session_id': str(self.session_id),
            'sequence_number': self.sequence_number,
            'received_timestamp': self.received_timestamp.isoformat(),
            'session_offset_ms': self.session_offset_ms,
            'duration_ms': self.duration_ms,
            'sample_rate': self.sample_rate,
            'encoding': self.encoding,
            'size_bytes': self.size_bytes
        }


@dataclass
class Transcription:
    """Transcription with timeline metadata"""
    transcription_id: UUID
    session_id: UUID
    audio_chunk_ids: List[UUID]
    text: str
    start_time_ms: int
    end_time_ms: int
    session_offset_ms: int
    confidence: float
    is_final: bool
    word_timestamps: List[WordTimestamp]
    created_at: datetime
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'transcription_id': str(self.transcription_id),
            'session_id': str(self.session_id),
            'audio_chunk_ids': [str(cid) for cid in self.audio_chunk_ids],
            'text': self.text,
            'start_time_ms': self.start_time_ms,
            'end_time_ms': self.end_time_ms,
            'session_offset_ms': self.session_offset_ms,
            'confidence': self.confidence,
            'is_final': self.is_final,
            'word_timestamps': [
                {
                    'word': wt.word,
                    'start_time_ms': wt.start_time_ms,
                    'end_time_ms': wt.end_time_ms,
                    'confidence': wt.confidence
                }
                for wt in self.word_timestamps
            ],
            'created_at': self.created_at.isoformat()
        }


@dataclass
class HelpEvent:
    """Help intervention event with context"""
    event_id: UUID
    session_id: UUID
    session_time_offset_ms: int
    trigger_transcriptions: List[str]
    audio_segment_ids: List[UUID]
    help_message: str
    audio_response: Optional[str] = None  # Base64 encoded
    response_timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.0
    reason: str = ""
    trigger_timestamps: List[str] = field(default_factory=list)  # ISO format timestamps
    accumulation_duration_ms: int = 0  # How long text was accumulated before help
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'event_id': str(self.event_id),
            'session_id': str(self.session_id),
            'session_time_offset_ms': self.session_time_offset_ms,
            'trigger_transcriptions': self.trigger_transcriptions,
            'trigger_timestamps': self.trigger_timestamps,
            'accumulation_duration_ms': self.accumulation_duration_ms,
            'audio_segment_ids': [str(sid) for sid in self.audio_segment_ids],
            'help_message': self.help_message,
            'audio_response': self.audio_response,
            'response_timestamp': self.response_timestamp.isoformat(),
            'confidence': self.confidence,
            'reason': self.reason
        }


@dataclass
class SessionMetrics:
    """Reading session metrics"""
    total_words: int = 0
    reading_speed_wpm: float = 0.0
    pause_count: int = 0
    total_pause_duration_ms: int = 0
    help_request_count: int = 0
    average_confidence: float = 0.0
    total_reading_time_ms: int = 0
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'total_words': self.total_words,
            'reading_speed_wpm': self.reading_speed_wpm,
            'pause_count': self.pause_count,
            'total_pause_duration_ms': self.total_pause_duration_ms,
            'help_request_count': self.help_request_count,
            'average_confidence': self.average_confidence,
            'total_reading_time_ms': self.total_reading_time_ms
        }


@dataclass
class ReadingSession:
    """Complete reading session with timeline"""
    session_id: UUID
    client_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    audio_chunks: List[AudioChunk] = field(default_factory=list)
    transcriptions: List[Transcription] = field(default_factory=list)
    help_events: List[HelpEvent] = field(default_factory=list)
    metrics: SessionMetrics = field(default_factory=SessionMetrics)
    
    @property
    def total_duration_ms(self) -> int:
        """Calculate total session duration"""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds() * 1000)
        return int((datetime.now() - self.start_time).total_seconds() * 1000)
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active"""
        return self.end_time is None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'session_id': str(self.session_id),
            'client_id': self.client_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_duration_ms': self.total_duration_ms,
            'is_active': self.is_active,
            'audio_chunks_count': len(self.audio_chunks),
            'transcriptions_count': len(self.transcriptions),
            'help_events_count': len(self.help_events),
            'metrics': self.metrics.to_dict()
        }
