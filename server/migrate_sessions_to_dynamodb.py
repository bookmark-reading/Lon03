#!/usr/bin/env python3
"""
Migrate Local Session Files to DynamoDB
Reads JSON session files and uploads them to DynamoDB
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID
from dynamodb_persistence import DynamoDBPersistence
from dynamodb_config import DynamoDBConfig
from analysis.analysis_models import SessionSummary, BatchMetrics, MiscueEvent, MiscueType


async def migrate_session_file(filepath: Path, dynamodb: DynamoDBPersistence, dry_run: bool = False):
    """Migrate a single session file to DynamoDB"""
    try:
        print(f"\n{'='*80}")
        print(f"Processing: {filepath.name}")
        print(f"{'='*80}")
        
        # Read JSON file
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Extract session ID from data or filename
        session_id_str = data.get('session_id')
        if not session_id_str:
            # Try to extract from filename: session_<uuid>_<timestamp>.json
            parts = filepath.stem.split('_')
            if len(parts) >= 2:
                session_id_str = parts[1]
            else:
                print(f"❌ Could not extract session_id from {filepath.name}")
                return False
        
        try:
            session_id = UUID(session_id_str)
        except ValueError:
            print(f"❌ Invalid session_id: {session_id_str}")
            return False
        
        print(f"Session ID: {session_id}")
        
        # Parse timestamps
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        
        print(f"Start: {start_time}")
        print(f"End: {end_time}")
        print(f"Duration: {data.get('total_duration_minutes', 0):.2f} minutes")
        
        # Create SessionSummary object
        session_summary = SessionSummary(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            total_words=data.get('total_words', 0),
            total_reading_time_minutes=data.get('total_duration_minutes', 0),
            average_wpm=data.get('average_wpm', 0),
            overall_accuracy=data.get('overall_accuracy'),
            average_confidence=data.get('average_confidence', 0),
            total_omissions=data.get('total_miscue_counts', {}).get('omissions', 0),
            total_insertions=data.get('total_miscue_counts', {}).get('insertions', 0),
            total_substitutions=data.get('total_miscue_counts', {}).get('substitutions', 0),
            total_repetitions=data.get('total_miscue_counts', {}).get('repetitions', 0),
            total_self_corrections=data.get('total_miscue_counts', {}).get('self_corrections', 0),
            total_hesitations=data.get('total_miscue_counts', {}).get('hesitations', 0),
            full_transcript=data.get('full_transcript', ''),
            expected_passage=data.get('expected_passage'),
            insights=data.get('insights', {})
        )
        
        # Parse miscue events if available
        if 'all_miscue_events' in data:
            for event_data in data['all_miscue_events']:
                try:
                    miscue_type = MiscueType(event_data['miscue_type'])
                    event = MiscueEvent(
                        miscue_type=miscue_type,
                        expected_word=event_data.get('expected_word'),
                        actual_word=event_data.get('actual_word'),
                        position=event_data.get('position'),
                        timestamp_ms=event_data.get('timestamp_ms')
                    )
                    session_summary.all_miscue_events.append(event)
                except (KeyError, ValueError) as e:
                    print(f"⚠️  Skipping invalid miscue event: {e}")
        
        # Parse batch metrics if available
        if 'batch_metrics' in data:
            for batch_data in data['batch_metrics']:
                try:
                    batch_id = UUID(batch_data['batch_id'])
                    batch_start = datetime.fromisoformat(batch_data['start_time'])
                    batch_end = datetime.fromisoformat(batch_data['end_time'])
                    
                    batch = BatchMetrics(
                        batch_id=batch_id,
                        session_id=session_id,
                        start_time=batch_start,
                        end_time=batch_end,
                        transcriptions=batch_data.get('transcriptions', []),
                        word_count=batch_data.get('word_count', 0),
                        words_per_minute=batch_data.get('words_per_minute', 0),
                        average_confidence=batch_data.get('average_confidence', 0),
                        omissions=batch_data.get('miscue_counts', {}).get('omissions', 0),
                        insertions=batch_data.get('miscue_counts', {}).get('insertions', 0),
                        substitutions=batch_data.get('miscue_counts', {}).get('substitutions', 0),
                        repetitions=batch_data.get('miscue_counts', {}).get('repetitions', 0),
                        self_corrections=batch_data.get('miscue_counts', {}).get('self_corrections', 0),
                        hesitations=batch_data.get('miscue_counts', {}).get('hesitations', 0),
                        expected_text=batch_data.get('expected_text'),
                        accuracy_percentage=batch_data.get('accuracy_percentage')
                    )
                    
                    # Parse batch miscue events
                    if 'miscue_events' in batch_data:
                        for event_data in batch_data['miscue_events']:
                            try:
                                miscue_type = MiscueType(event_data['miscue_type'])
                                event = MiscueEvent(
                                    miscue_type=miscue_type,
                                    expected_word=event_data.get('expected_word'),
                                    actual_word=event_data.get('actual_word'),
                                    position=event_data.get('position'),
                                    timestamp_ms=event_data.get('timestamp_ms')
                                )
                                batch.miscue_events.append(event)
                            except (KeyError, ValueError):
                                pass
                    
                    session_summary.batch_metrics.append(batch)
                    
                except (KeyError, ValueError) as e:
                    print(f"⚠️  Skipping invalid batch metric: {e}")
        
        # Display summary
        print(f"\n📊 Summary:")
        print(f"  Total Words: {session_summary.total_words}")
        print(f"  Average WPM: {session_summary.average_wpm:.1f}")
        print(f"  Total Miscues: {session_summary.total_omissions + session_summary.total_insertions + session_summary.total_substitutions + session_summary.total_repetitions + session_summary.total_hesitations}")
        print(f"  Batch Metrics: {len(session_summary.batch_metrics)}")
        print(f"  Miscue Events: {len(session_summary.all_miscue_events)}")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - Would save to DynamoDB")
            return True
        
        # Save to DynamoDB
        print(f"\n💾 Saving to DynamoDB...")
        
        # Save session summary
        success = await dynamodb.save_session_summary(session_summary)
        
        if not success:
            print(f"❌ Failed to save session summary")
            return False
        
        # Save batch metrics
        for batch in session_summary.batch_metrics:
            await dynamodb.save_batch_metrics(batch)
        
        # Wait for writes to complete
        await asyncio.sleep(1)
        
        print(f"✅ Successfully migrated {filepath.name}")
        return True
        
    except Exception as e:
        print(f"❌ Error migrating {filepath.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def migrate_all_sessions(sessions_dir: str = 'sessions', dry_run: bool = False):
    """Migrate all session files in directory"""
    print(f"\n{'='*80}")
    print(f"Session Migration Tool")
    print(f"{'='*80}")
    
    if not DynamoDBConfig.is_enabled():
        print("\n❌ DynamoDB persistence is not enabled!")
        print("Set ENABLE_DYNAMODB_PERSISTENCE=true in .env")
        return
    
    # Initialize DynamoDB
    dynamodb = DynamoDBPersistence()
    
    # Start workers
    print("\n🚀 Starting DynamoDB workers...")
    await dynamodb.start_write_worker()
    
    # Find session files
    sessions_path = Path(sessions_dir)
    if not sessions_path.exists():
        print(f"\n❌ Directory not found: {sessions_dir}")
        return
    
    json_files = sorted(sessions_path.glob('session_*.json'))
    
    if not json_files:
        print(f"\n⚠️  No session files found in {sessions_dir}")
        return
    
    print(f"\n📁 Found {len(json_files)} session files")
    
    if dry_run:
        print(f"\n🔍 DRY RUN MODE - No data will be written to DynamoDB")
    
    # Migrate each file
    success_count = 0
    fail_count = 0
    
    for filepath in json_files:
        success = await migrate_session_file(filepath, dynamodb, dry_run)
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    # Stop workers
    print(f"\n🛑 Stopping DynamoDB workers...")
    await dynamodb.stop_workers()
    
    # Summary
    print(f"\n{'='*80}")
    print(f"Migration Complete")
    print(f"{'='*80}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📊 Total: {len(json_files)}")
    
    if dry_run:
        print(f"\n💡 Run without --dry-run to actually migrate data")


async def main():
    """Main execution"""
    dry_run = '--dry-run' in sys.argv
    
    if len(sys.argv) > 1 and sys.argv[1] not in ['--dry-run']:
        # Migrate specific file
        filepath = Path(sys.argv[1])
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            return
        
        dynamodb = DynamoDBPersistence()
        await dynamodb.start_write_worker()
        
        await migrate_session_file(filepath, dynamodb, dry_run)
        
        await dynamodb.stop_workers()
    else:
        # Migrate all files
        await migrate_all_sessions(dry_run=dry_run)


if __name__ == '__main__':
    print("\nUsage:")
    print(f"  python {sys.argv[0]} [--dry-run]              # Migrate all sessions")
    print(f"  python {sys.argv[0]} <file.json> [--dry-run]  # Migrate specific session")
    print()
    
    asyncio.run(main())
