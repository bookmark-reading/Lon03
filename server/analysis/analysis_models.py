"""
Data models for reading analysis results
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID
from enum import Enum


class MiscueType(Enum):
    """Types of reading miscues"""
    OMISSION = "omission"
    INSERTION = "insertion"
    SUBSTITUTION = "substitution"
    REPETITION = "repetition"
    SELF_CORRECTION = "self_correction"
    HESITATION = "hesitation"


@dataclass
class MiscueEvent:
    """Individual miscue event detected in reading"""
    miscue_type: MiscueType
    expected_word: Optional[str] = None
    actual_word: Optional[str] = None
    position: Optional[int] = None  # Position in passage
    timestamp_ms: Optional[int] = None
    
    def to_dict(self):
        return {
            'miscue_type': self.miscue_type.value,
            'expected_word': self.expected_word,
            'actual_word': self.actual_word,
            'position': self.position,
            'timestamp_ms': self.timestamp_ms
        }


@dataclass
class BatchMetrics:
    """Metrics for a batch of transcriptions (e.g., per minute)"""
    batch_id: UUID
    session_id: UUID
    start_time: datetime
    end_time: datetime
    transcriptions: List[str]
    
    # Basic metrics
    word_count: int = 0
    words_per_minute: float = 0.0
    average_confidence: float = 0.0
    
    # Miscue counts
    omissions: int = 0
    insertions: int = 0
    substitutions: int = 0
    repetitions: int = 0
    self_corrections: int = 0
    hesitations: int = 0
    
    # Detailed miscue events
    miscue_events: List[MiscueEvent] = field(default_factory=list)
    
    # Passage comparison (if available)
    expected_text: Optional[str] = None
    accuracy_percentage: Optional[float] = None
    
    def to_dict(self):
        return {
            'batch_id': str(self.batch_id),
            'session_id': str(self.session_id),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': (self.end_time - self.start_time).total_seconds(),
            'word_count': self.word_count,
            'words_per_minute': self.words_per_minute,
            'average_confidence': self.average_confidence,
            'miscue_counts': {
                'omissions': self.omissions,
                'insertions': self.insertions,
                'substitutions': self.substitutions,
                'repetitions': self.repetitions,
                'self_corrections': self.self_corrections,
                'hesitations': self.hesitations,
                'total': (self.omissions + self.insertions + self.substitutions + 
                         self.repetitions + self.self_corrections + self.hesitations)
            },
            'miscue_events': [event.to_dict() for event in self.miscue_events],
            'expected_text': self.expected_text,
            'accuracy_percentage': self.accuracy_percentage,
            'transcriptions': self.transcriptions
        }


@dataclass
class SessionSummary:
    """Complete session analysis summary"""
    session_id: UUID
    start_time: datetime
    end_time: datetime
    
    # Overall metrics
    total_words: int = 0
    total_reading_time_minutes: float = 0.0
    average_wpm: float = 0.0
    overall_accuracy: Optional[float] = None
    average_confidence: float = 0.0
    
    # Total miscue counts
    total_omissions: int = 0
    total_insertions: int = 0
    total_substitutions: int = 0
    total_repetitions: int = 0
    total_self_corrections: int = 0
    total_hesitations: int = 0
    
    # Batch metrics over time
    batch_metrics: List[BatchMetrics] = field(default_factory=list)
    
    # All miscue events across session
    all_miscue_events: List[MiscueEvent] = field(default_factory=list)
    
    # Full transcript
    full_transcript: str = ""
    expected_passage: Optional[str] = None
    
    # Additional insights
    insights: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            'session_id': str(self.session_id),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'total_duration_minutes': self.total_reading_time_minutes,
            'total_words': self.total_words,
            'average_wpm': self.average_wpm,
            'overall_accuracy': self.overall_accuracy,
            'average_confidence': self.average_confidence,
            'total_miscue_counts': {
                'omissions': self.total_omissions,
                'insertions': self.total_insertions,
                'substitutions': self.total_substitutions,
                'repetitions': self.total_repetitions,
                'self_corrections': self.total_self_corrections,
                'hesitations': self.total_hesitations,
                'total': (self.total_omissions + self.total_insertions + 
                         self.total_substitutions + self.total_repetitions +
                         self.total_self_corrections + self.total_hesitations)
            },
            'batch_metrics': [batch.to_dict() for batch in self.batch_metrics],
            'all_miscue_events': [event.to_dict() for event in self.all_miscue_events],
            'full_transcript': self.full_transcript,
            'expected_passage': self.expected_passage,
            'insights': self.insights
        }


@dataclass
class AnalysisResult:
    """Result from LLM analysis"""
    cleaned_passage: Optional[str] = None
    kpis: Dict = field(default_factory=dict)
    raw_response: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self):
        return {
            'cleaned_passage': self.cleaned_passage,
            'kpis': self.kpis,
            'raw_response': self.raw_response,
            'error': self.error
        }
