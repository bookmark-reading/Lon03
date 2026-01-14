#!/usr/bin/env python3
"""
Test DynamoDB Integration
Creates a test reading session and verifies it's saved to DynamoDB
"""
import asyncio
from datetime import datetime
from uuid import uuid4
from models import ReadingSession, AudioChunk, Transcription, HelpEvent, SessionMetrics, WordTimestamp
from dynamodb_persistence import DynamoDBPersistence
from dynamodb_config import DynamoDBConfig


async def test_session_persistence():
    """Test creating and saving a reading session"""
    print("\n" + "="*60)
    print("DynamoDB Integration Test")
    print("="*60 + "\n")
    
    # Check configuration
    print("Configuration:")
    config = DynamoDBConfig.get_config_summary()
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    if not DynamoDBConfig.is_enabled():
        print("\n❌ DynamoDB persistence is DISABLED")
        print("   Set ENABLE_DYNAMODB_PERSISTENCE=true in .env")
        return
    
    print("\n✅ DynamoDB persistence is ENABLED\n")
    
    # Initialize persistence layer
    print("Initializing persistence layer...")
    persistence = DynamoDBPersistence()
    
    # Start workers
    print("Starting background workers...")
    await persistence.start_write_worker()
    
    # Create test session
    session_id = uuid4()
    print(f"\nCreating test session: {session_id}")
    
    session = ReadingSession(
        session_id=session_id,
        client_id="test-client-123",
        start_time=datetime.now(),
        metrics=SessionMetrics()
    )
    
    # Save session
    print("Saving session to DynamoDB...")
    success = await persistence.save_session(session)
    
    if success:
        print("✅ Session queued for write")
    else:
        print("❌ Failed to queue session")
        return
    
    # Create test audio chunk
    print("\nCreating test audio chunk...")
    chunk = AudioChunk(
        chunk_id=uuid4(),
        client_id="test-client-123",
        session_id=session_id,
        sequence_number=1,
        received_timestamp=datetime.now(),
        session_offset_ms=0,
        duration_ms=1000,
        sample_rate=16000,
        encoding="webm",
        size_bytes=8192,
        audio_data=b"test_audio_data"
    )
    
    success = await persistence.save_audio_chunk(chunk)
    if success:
        print("✅ Audio chunk queued")
    
    # Create test transcription
    print("\nCreating test transcription...")
    transcription = Transcription(
        transcription_id=uuid4(),
        session_id=session_id,
        audio_chunk_ids=[chunk.chunk_id],
        text="The quick brown fox jumps over the lazy dog",
        start_time_ms=0,
        end_time_ms=1000,
        session_offset_ms=0,
        confidence=0.95,
        is_final=True,
        word_timestamps=[
            WordTimestamp(word="The", start_time_ms=0, end_time_ms=100, confidence=0.98),
            WordTimestamp(word="quick", start_time_ms=100, end_time_ms=250, confidence=0.96),
            WordTimestamp(word="brown", start_time_ms=250, end_time_ms=400, confidence=0.94),
        ],
        created_at=datetime.now()
    )
    
    success = await persistence.save_transcription(transcription)
    if success:
        print("✅ Transcription queued")
    
    # Create test help event
    print("\nCreating test help event...")
    help_event = HelpEvent(
        event_id=uuid4(),
        session_id=session_id,
        session_time_offset_ms=5000,
        trigger_transcriptions=["um", "uh", "um"],
        trigger_timestamps=["2026-01-14T10:00:00", "2026-01-14T10:00:02", "2026-01-14T10:00:04"],
        accumulation_duration_ms=4000,
        audio_segment_ids=[chunk.chunk_id],
        help_message="Take your time and sound out the word",
        audio_response=b"test_audio_response",
        response_timestamp=datetime.now(),
        confidence=0.85,
        reason="Multiple hesitations detected"
    )
    
    success = await persistence.save_help_event(help_event)
    if success:
        print("✅ Help event queued")
    
    # Wait for writes to complete
    print("\nWaiting for background workers to process queue...")
    await asyncio.sleep(3)
    
    # Flush remaining items
    print("Flushing remaining items...")
    await persistence.flush_all_queues()
    
    # Check queue depths
    depths = persistence.get_queue_depth()
    print(f"\nQueue depths: {depths}")
    
    # Wait a bit more for final writes
    await asyncio.sleep(2)
    
    # Try to read back the session
    print(f"\nReading session back from DynamoDB...")
    metadata = await persistence.get_session_metadata(session_id)
    
    if metadata:
        print("✅ Session found in DynamoDB!")
        print(f"\nSession metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
    else:
        print("⚠️  Session not found yet (may still be processing)")
    
    # Stop workers
    print("\nStopping workers...")
    await persistence.stop_workers()
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)
    print(f"\nTo verify in DynamoDB:")
    print(f"  python query_existing_data.py")
    print(f"\nOr check AWS Console:")
    print(f"  Table: reading_sessions")
    print(f"  Region: us-west-2")
    print(f"  Look for PK: SESSION#{session_id}")
    print()


async def test_query_operations():
    """Test querying data from DynamoDB"""
    print("\n" + "="*60)
    print("Testing Query Operations")
    print("="*60 + "\n")
    
    persistence = DynamoDBPersistence()
    
    # Query sessions by date
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"Querying sessions for date: {today}")
    
    sessions = await persistence.get_sessions_by_date(today, limit=10)
    
    if sessions:
        print(f"✅ Found {len(sessions)} sessions")
        for session in sessions:
            print(f"  - {session.get('session_id')} (Client: {session.get('client_id')})")
    else:
        print("No sessions found for today")
    
    print()


def main():
    """Main execution"""
    # Run async test
    asyncio.run(test_session_persistence())
    
    # Optionally test queries
    # asyncio.run(test_query_operations())


if __name__ == '__main__':
    main()
