"""
Audio buffer manager for tracking audio chunks and timeline
"""
import struct
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from models import AudioChunk, ReadingSession


class AudioBufferManager:
    """Manages audio chunks and timeline for reading sessions"""
    
    def __init__(self, dynamodb_persistence=None):
        self.sessions: Dict[str, ReadingSession] = {}
        self.chunk_sequences: Dict[str, int] = {}  # client_id -> sequence number
        self.dynamodb = dynamodb_persistence  # Optional DynamoDB persistence
        
    def create_session(self, client_id: str) -> ReadingSession:
        """Create a new reading session"""
        session = ReadingSession(
            session_id=uuid4(),
            client_id=client_id,
            start_time=datetime.now()
        )
        self.sessions[client_id] = session
        self.chunk_sequences[client_id] = 0
        
        # Persist to DynamoDB if enabled
        if self.dynamodb:
            import asyncio
            asyncio.create_task(self.dynamodb.save_session(session))
        
        return session
    
    def get_session(self, client_id: str) -> Optional[ReadingSession]:
        """Get active session for client"""
        return self.sessions.get(client_id)
    
    def end_session(self, client_id: str):
        """End a reading session"""
        if client_id in self.sessions:
            self.sessions[client_id].end_time = datetime.now()
            self._calculate_final_metrics(client_id)
            
            # Persist to DynamoDB if enabled
            if self.dynamodb:
                import asyncio
                session = self.sessions[client_id]
                asyncio.create_task(self.dynamodb.end_session(session.session_id, session.end_time))
                asyncio.create_task(self.dynamodb.update_session_metrics(
                    session.session_id,
                    session.metrics.to_dict()
                ))
    
    def store_chunk(
        self,
        client_id: str,
        audio_bytes: bytes,
        sample_rate: int,
        encoding: str,
        store_audio_data: bool = False
    ) -> AudioChunk:
        """Store audio chunk with metadata"""
        # Get or create session
        session = self.sessions.get(client_id)
        if not session:
            session = self.create_session(client_id)
        
        # Calculate duration
        duration_ms = self.calculate_audio_duration(audio_bytes, sample_rate, encoding)
        
        # Get sequence number
        sequence = self.chunk_sequences.get(client_id, 0)
        self.chunk_sequences[client_id] = sequence + 1
        
        # Calculate session offset
        session_offset_ms = sum(chunk.duration_ms for chunk in session.audio_chunks)
        
        # Create audio chunk
        chunk = AudioChunk(
            chunk_id=uuid4(),
            client_id=client_id,
            session_id=session.session_id,
            sequence_number=sequence,
            received_timestamp=datetime.now(),
            session_offset_ms=session_offset_ms,
            duration_ms=duration_ms,
            sample_rate=sample_rate,
            encoding=encoding,
            size_bytes=len(audio_bytes),
            audio_data=audio_bytes if store_audio_data else None
        )
        
        # Add to session
        session.audio_chunks.append(chunk)
        
        # Persist to DynamoDB if enabled
        if self.dynamodb:
            import asyncio
            asyncio.create_task(self.dynamodb.save_audio_chunk(chunk))
        
        return chunk
    
    def get_chunks_in_range(
        self,
        client_id: str,
        start_time_ms: int,
        end_time_ms: int
    ) -> List[AudioChunk]:
        """Get audio chunks within a time range"""
        session = self.sessions.get(client_id)
        if not session:
            return []
        
        chunks = []
        for chunk in session.audio_chunks:
            chunk_end = chunk.session_offset_ms + chunk.duration_ms
            # Check if chunk overlaps with range
            if chunk.session_offset_ms <= end_time_ms and chunk_end >= start_time_ms:
                chunks.append(chunk)
        
        return chunks
    
    def get_current_session_time(self, client_id: str) -> int:
        """Get current session time in milliseconds"""
        session = self.sessions.get(client_id)
        if not session:
            return 0
        return session.total_duration_ms
    
    def calculate_audio_duration(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        encoding: str
    ) -> int:
        """Calculate audio duration in milliseconds"""
        if encoding.lower() == "pcm":
            return self._calculate_pcm_duration(audio_bytes, sample_rate)
        elif encoding.lower() in ["ogg-opus", "opus"]:
            return self._estimate_opus_duration(audio_bytes, sample_rate)
        else:
            # Fallback estimation
            return self._estimate_duration_by_size(audio_bytes, sample_rate)
    
    def _calculate_pcm_duration(self, audio_bytes: bytes, sample_rate: int) -> int:
        """Calculate PCM audio duration"""
        # PCM: 16-bit samples (2 bytes per sample), mono
        bytes_per_sample = 2
        num_samples = len(audio_bytes) / bytes_per_sample
        duration_seconds = num_samples / sample_rate
        return int(duration_seconds * 1000)
    
    def _estimate_opus_duration(self, audio_bytes: bytes, sample_rate: int) -> int:
        """Estimate Opus audio duration (compressed format)"""
        # Opus typical bitrate: 24-40 kbps for speech
        # Use conservative estimate of 32 kbps
        bitrate = 32000  # bits per second
        bytes_per_second = bitrate / 8
        duration_seconds = len(audio_bytes) / bytes_per_second
        return int(duration_seconds * 1000)
    
    def _estimate_duration_by_size(self, audio_bytes: bytes, sample_rate: int) -> int:
        """Fallback duration estimation"""
        # Assume average compression ratio
        estimated_samples = len(audio_bytes) / 2  # Conservative estimate
        duration_seconds = estimated_samples / sample_rate
        return int(duration_seconds * 1000)
    
    def get_session_timeline(self, client_id: str) -> Dict:
        """Get complete session timeline"""
        session = self.sessions.get(client_id)
        if not session:
            return {}
        
        return {
            'session_id': str(session.session_id),
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'total_duration_ms': session.total_duration_ms,
            'audio_chunks': [chunk.to_dict() for chunk in session.audio_chunks],
            'transcriptions': [t.to_dict() for t in session.transcriptions],
            'help_events': [h.to_dict() for h in session.help_events],
            'metrics': session.metrics.to_dict()
        }
    
    def _calculate_final_metrics(self, client_id: str):
        """Calculate final session metrics"""
        session = self.sessions.get(client_id)
        if not session:
            return
        
        metrics = session.metrics
        
        # Calculate total words
        metrics.total_words = sum(
            len(t.text.split()) for t in session.transcriptions if t.is_final
        )
        
        # Calculate reading speed (WPM)
        if session.total_duration_ms > 0:
            duration_minutes = session.total_duration_ms / 60000
            metrics.reading_speed_wpm = metrics.total_words / duration_minutes if duration_minutes > 0 else 0
        
        # Calculate average confidence
        confidences = [t.confidence for t in session.transcriptions if t.is_final]
        if confidences:
            metrics.average_confidence = sum(confidences) / len(confidences)
        
        # Help request count
        metrics.help_request_count = len(session.help_events)
        
        # Total reading time
        metrics.total_reading_time_ms = session.total_duration_ms
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old inactive sessions"""
        current_time = datetime.now()
        clients_to_remove = []
        
        for client_id, session in self.sessions.items():
            if session.end_time:
                age_hours = (current_time - session.end_time).total_seconds() / 3600
                if age_hours > max_age_hours:
                    clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.sessions[client_id]
            if client_id in self.chunk_sequences:
                del self.chunk_sequences[client_id]
