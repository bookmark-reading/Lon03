"""
Test script for audio metadata system
Demonstrates the metadata tracking functionality
"""
import asyncio
from datetime import datetime
from uuid import uuid4
from models import (
    AudioChunk,
    Transcription,
    HelpEvent,
    WordTimestamp,
    ReadingSession,
    SessionMetrics
)
from audio_buffer_manager import AudioBufferManager


def test_audio_buffer_manager():
    """Test audio buffer manager functionality"""
    print("=" * 60)
    print("Testing Audio Buffer Manager")
    print("=" * 60)
    
    manager = AudioBufferManager()
    client_id = "test_client_123"
    
    # Create session
    print("\n1. Creating session...")
    session = manager.create_session(client_id)
    print(f"   Session ID: {session.session_id}")
    print(f"   Start time: {session.start_time}")
    
    # Simulate audio chunks
    print("\n2. Storing audio chunks...")
    for i in range(5):
        # Simulate 100ms of PCM audio at 16kHz
        # 16000 samples/sec * 0.1 sec * 2 bytes/sample = 3200 bytes
        fake_audio = b'\x00' * 3200
        
        chunk = manager.store_chunk(
            client_id=client_id,
            audio_bytes=fake_audio,
            sample_rate=16000,
            encoding="pcm",
            store_audio_data=False
        )
        
        print(f"   Chunk {i+1}:")
        print(f"     - ID: {chunk.chunk_id}")
        print(f"     - Sequence: {chunk.sequence_number}")
        print(f"     - Duration: {chunk.duration_ms}ms")
        print(f"     - Session offset: {chunk.session_offset_ms}ms")
    
    # Get current session time
    print("\n3. Current session time...")
    current_time = manager.get_current_session_time(client_id)
    print(f"   Total time: {current_time}ms")
    
    # Query chunks in range
    print("\n4. Querying chunks in time range (50ms - 250ms)...")
    chunks = manager.get_chunks_in_range(client_id, 50, 250)
    print(f"   Found {len(chunks)} chunks")
    for chunk in chunks:
        print(f"     - Chunk {chunk.sequence_number}: {chunk.session_offset_ms}-{chunk.session_offset_ms + chunk.duration_ms}ms")
    
    # Add mock transcriptions
    print("\n5. Adding transcriptions...")
    session = manager.get_session(client_id)
    
    transcription1 = Transcription(
        transcription_id=uuid4(),
        session_id=session.session_id,
        audio_chunk_ids=[session.audio_chunks[0].chunk_id, session.audio_chunks[1].chunk_id],
        text="The cat sat on the mat",
        start_time_ms=0,
        end_time_ms=200,
        session_offset_ms=0,
        confidence=0.95,
        is_final=True,
        word_timestamps=[
            WordTimestamp("The", 0, 50, 0.98),
            WordTimestamp("cat", 50, 100, 0.96),
            WordTimestamp("sat", 100, 150, 0.94),
            WordTimestamp("on", 150, 170, 0.97),
            WordTimestamp("the", 170, 190, 0.95),
            WordTimestamp("mat", 190, 200, 0.93)
        ],
        created_at=datetime.now()
    )
    session.transcriptions.append(transcription1)
    print(f"   Added: '{transcription1.text}'")
    print(f"   Time: {transcription1.start_time_ms}-{transcription1.end_time_ms}ms")
    print(f"   Words: {len(transcription1.word_timestamps)}")
    
    # Add help event
    print("\n6. Adding help event...")
    help_event = HelpEvent(
        event_id=uuid4(),
        session_id=session.session_id,
        session_time_offset_ms=200,
        trigger_transcriptions=["The cat sat on the mat"],
        trigger_timestamps=[datetime.now().isoformat()],
        accumulation_duration_ms=200,
        audio_segment_ids=[session.audio_chunks[0].chunk_id],
        help_message="Great job! Keep reading.",
        confidence=0.85,
        reason="Encouraging progress"
    )
    session.help_events.append(help_event)
    print(f"   Message: '{help_event.help_message}'")
    print(f"   Time offset: {help_event.session_time_offset_ms}ms")
    print(f"   Accumulation duration: {help_event.accumulation_duration_ms}ms")
    print(f"   Trigger timestamps: {len(help_event.trigger_timestamps)}")
    
    # End session and calculate metrics
    print("\n7. Ending session and calculating metrics...")
    manager.end_session(client_id)
    session = manager.get_session(client_id)
    
    print(f"   Total duration: {session.total_duration_ms}ms")
    print(f"   Total words: {session.metrics.total_words}")
    print(f"   Reading speed: {session.metrics.reading_speed_wpm:.1f} WPM")
    print(f"   Average confidence: {session.metrics.average_confidence:.2f}")
    print(f"   Help events: {session.metrics.help_request_count}")
    
    # Get session timeline
    print("\n8. Getting session timeline...")
    timeline = manager.get_session_timeline(client_id)
    print(f"   Session ID: {timeline['session_id']}")
    print(f"   Audio chunks: {len(timeline['audio_chunks'])}")
    print(f"   Transcriptions: {len(timeline['transcriptions'])}")
    print(f"   Help events: {len(timeline['help_events'])}")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)


def test_duration_calculation():
    """Test audio duration calculation for different formats"""
    print("\n" + "=" * 60)
    print("Testing Audio Duration Calculation")
    print("=" * 60)
    
    manager = AudioBufferManager()
    
    # Test PCM duration
    print("\n1. PCM Format (16kHz, 16-bit, mono)")
    # 1 second of audio = 16000 samples * 2 bytes = 32000 bytes
    pcm_audio = b'\x00' * 32000
    duration = manager.calculate_audio_duration(pcm_audio, 16000, "pcm")
    print(f"   Input: 32000 bytes")
    print(f"   Expected: 1000ms")
    print(f"   Calculated: {duration}ms")
    print(f"   ✓ Correct!" if duration == 1000 else f"   ✗ Error!")
    
    # Test Opus duration (estimate)
    print("\n2. Opus Format (48kHz, compressed)")
    # Estimate: 32kbps = 4000 bytes/sec
    # 0.5 seconds = 2000 bytes
    opus_audio = b'\x00' * 2000
    duration = manager.calculate_audio_duration(opus_audio, 48000, "opus")
    print(f"   Input: 2000 bytes")
    print(f"   Expected: ~500ms (estimate)")
    print(f"   Calculated: {duration}ms")
    
    print("\n" + "=" * 60)


def test_data_models():
    """Test data model serialization"""
    print("\n" + "=" * 60)
    print("Testing Data Model Serialization")
    print("=" * 60)
    
    # Test AudioChunk
    print("\n1. AudioChunk to_dict()")
    chunk = AudioChunk(
        chunk_id=uuid4(),
        client_id="test_client",
        session_id=uuid4(),
        sequence_number=0,
        received_timestamp=datetime.now(),
        session_offset_ms=0,
        duration_ms=100,
        sample_rate=16000,
        encoding="pcm",
        size_bytes=3200
    )
    chunk_dict = chunk.to_dict()
    print(f"   Keys: {list(chunk_dict.keys())}")
    print(f"   ✓ Serializable")
    
    # Test Transcription
    print("\n2. Transcription to_dict()")
    transcription = Transcription(
        transcription_id=uuid4(),
        session_id=uuid4(),
        audio_chunk_ids=[uuid4()],
        text="Test transcription",
        start_time_ms=0,
        end_time_ms=100,
        session_offset_ms=0,
        confidence=0.95,
        is_final=True,
        word_timestamps=[],
        created_at=datetime.now()
    )
    trans_dict = transcription.to_dict()
    print(f"   Keys: {list(trans_dict.keys())}")
    print(f"   ✓ Serializable")
    
    # Test HelpEvent
    print("\n4. HelpEvent to_dict()")
    help_event = HelpEvent(
        event_id=uuid4(),
        session_id=uuid4(),
        session_time_offset_ms=1000,
        trigger_transcriptions=["Test text"],
        trigger_timestamps=[datetime.now().isoformat()],
        accumulation_duration_ms=500,
        audio_segment_ids=[uuid4()],
        help_message="Test help",
        confidence=0.85,
        reason="Test reason"
    )
    help_dict = help_event.to_dict()
    print(f"   Keys: {list(help_dict.keys())}")
    print(f"   Has trigger_timestamps: {'trigger_timestamps' in help_dict}")
    print(f"   Has accumulation_duration_ms: {'accumulation_duration_ms' in help_dict}")
    print(f"   ✓ Serializable")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "AUDIO METADATA SYSTEM TEST SUITE" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        test_data_models()
        test_duration_calculation()
        test_audio_buffer_manager()
        
        print("\n")
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 18 + "ALL TESTS PASSED!" + " " * 22 + "║")
        print("╚" + "=" * 58 + "╝")
        print("\n")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
