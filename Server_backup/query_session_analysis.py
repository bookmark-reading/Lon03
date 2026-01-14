#!/usr/bin/env python3
"""
Query Session Analysis from DynamoDB
Retrieves complete session data including batch metrics and summaries
"""
import asyncio
import sys
from uuid import UUID
from datetime import datetime
from dynamodb_persistence import DynamoDBPersistence
from dynamodb_config import DynamoDBConfig


async def query_session(session_id: str):
    """Query complete session data"""
    print(f"\n{'='*80}")
    print(f"Querying Session: {session_id}")
    print(f"{'='*80}\n")
    
    try:
        # Initialize DynamoDB persistence
        dynamodb = DynamoDBPersistence()
        
        # Convert string to UUID
        session_uuid = UUID(session_id)
        
        # Get complete session data
        data = await dynamodb.get_complete_session_data(session_uuid)
        
        if not data or not data.get('session_metadata'):
            print(f"❌ Session not found: {session_id}")
            return
        
        # Display session metadata
        print("📊 SESSION METADATA")
        print("-" * 80)
        metadata = data['session_metadata']
        print(f"Session ID: {metadata['session_id']}")
        print(f"Client ID: {metadata['client_id']}")
        print(f"Start Time: {metadata['start_time']}")
        print(f"End Time: {metadata.get('end_time', 'N/A')}")
        print(f"Duration: {metadata['total_duration_ms'] / 1000:.1f}s")
        print(f"Active: {metadata['is_active']}")
        print(f"\nCounts:")
        print(f"  Audio Chunks: {metadata['audio_chunks_count']}")
        print(f"  Transcriptions: {metadata['transcriptions_count']}")
        print(f"  Help Events: {metadata['help_events_count']}")
        
        # Display metrics
        print(f"\n📈 READING METRICS")
        print("-" * 80)
        metrics = metadata['metrics']
        print(f"Total Words: {metrics['TotalWords']}")
        print(f"Reading Speed: {metrics['ReadingSpeedWpm']:.1f} WPM")
        print(f"Average Confidence: {metrics['AverageConfidence']:.1%}")
        print(f"Pause Count: {metrics['PauseCount']}")
        print(f"Total Pause Duration: {metrics['TotalPauseDurationMs'] / 1000:.1f}s")
        print(f"Help Requests: {metrics['HelpRequestCount']}")
        print(f"Total Reading Time: {metrics['TotalReadingTimeMs'] / 1000:.1f}s")
        
        # Display transcriptions
        transcriptions = data.get('transcriptions', [])
        if transcriptions:
            print(f"\n📝 TRANSCRIPTIONS ({len(transcriptions)})")
            print("-" * 80)
            for i, trans in enumerate(transcriptions[:5], 1):  # Show first 5
                print(f"{i}. [{trans['start_time_ms']}ms - {trans['end_time_ms']}ms]")
                print(f"   Text: {trans['text']}")
                print(f"   Confidence: {trans['confidence']:.1%}")
            if len(transcriptions) > 5:
                print(f"   ... and {len(transcriptions) - 5} more")
        
        # Display help events
        help_events = data.get('help_events', [])
        if help_events:
            print(f"\n🆘 HELP EVENTS ({len(help_events)})")
            print("-" * 80)
            for i, event in enumerate(help_events, 1):
                print(f"{i}. [{event['session_time_offset_ms']}ms]")
                print(f"   Message: {event['help_message']}")
                print(f"   Confidence: {event['confidence']:.1%}")
                print(f"   Reason: {event['reason']}")
                print(f"   Triggers: {len(event['trigger_transcriptions'])} transcriptions")
        
        # Display batch metrics
        batch_metrics = data.get('batch_metrics', [])
        if batch_metrics:
            print(f"\n📊 BATCH METRICS ({len(batch_metrics)} batches)")
            print("-" * 80)
            for i, batch in enumerate(batch_metrics, 1):
                print(f"\nBatch {i}: {batch['batch_id'][:8]}...")
                print(f"  Time: {batch['start_time']} to {batch['end_time']}")
                print(f"  Duration: {batch['duration_seconds']:.1f}s")
                print(f"  Words: {batch['word_count']} ({batch['words_per_minute']:.1f} WPM)")
                print(f"  Confidence: {batch['average_confidence']:.1%}")
                if batch.get('accuracy_percentage'):
                    print(f"  Accuracy: {batch['accuracy_percentage']:.1f}%")
                
                miscues = batch['miscue_counts']
                total_miscues = miscues['Total']
                if total_miscues > 0:
                    print(f"  Miscues: {total_miscues} total")
                    print(f"    - Omissions: {miscues['Omissions']}")
                    print(f"    - Insertions: {miscues['Insertions']}")
                    print(f"    - Substitutions: {miscues['Substitutions']}")
                    print(f"    - Repetitions: {miscues['Repetitions']}")
                    print(f"    - Hesitations: {miscues['Hesitations']}")
        
        # Display session summary
        summary = data.get('session_summary')
        if summary:
            print(f"\n📋 SESSION SUMMARY")
            print("-" * 80)
            print(f"Duration: {summary['total_duration_minutes']:.2f} minutes")
            print(f"Total Words: {summary['total_words']}")
            print(f"Average WPM: {summary['average_wpm']:.1f}")
            if summary.get('overall_accuracy'):
                print(f"Overall Accuracy: {summary['overall_accuracy']:.1f}%")
            print(f"Average Confidence: {summary['average_confidence']:.1%}")
            
            total_miscues = summary['total_miscue_counts']
            print(f"\nTotal Miscues: {total_miscues['Total']}")
            print(f"  - Omissions: {total_miscues['Omissions']}")
            print(f"  - Insertions: {total_miscues['Insertions']}")
            print(f"  - Substitutions: {total_miscues['Substitutions']}")
            print(f"  - Repetitions: {total_miscues['Repetitions']}")
            print(f"  - Self-Corrections: {total_miscues['SelfCorrections']}")
            print(f"  - Hesitations: {total_miscues['Hesitations']}")
            
            if summary.get('insights'):
                print(f"\n💡 Insights:")
                for key, value in summary['insights'].items():
                    print(f"  {key}: {value}")
            
            if summary.get('full_transcript'):
                print(f"\n📄 Full Transcript:")
                print(f"  {summary['full_transcript'][:200]}...")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Error querying session: {e}")
        import traceback
        traceback.print_exc()


async def list_recent_sessions(limit: int = 10):
    """List recent sessions"""
    print(f"\n{'='*80}")
    print(f"Recent Sessions (limit: {limit})")
    print(f"{'='*80}\n")
    
    try:
        dynamodb = DynamoDBPersistence()
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Query sessions by date
        sessions = await dynamodb.get_sessions_by_date(today, limit=limit)
        
        if not sessions:
            print(f"No sessions found for {today}")
            return
        
        print(f"Found {len(sessions)} sessions:\n")
        
        for i, session in enumerate(sessions, 1):
            print(f"{i}. Session ID: {session['session_id']}")
            print(f"   Client: {session['client_id']}")
            print(f"   Start: {session['start_time']}")
            print(f"   Duration: {session['total_duration_ms'] / 1000:.1f}s")
            print(f"   Words: {session['metrics']['TotalWords']}")
            print(f"   WPM: {session['metrics']['ReadingSpeedWpm']:.1f}")
            print()
        
    except Exception as e:
        print(f"❌ Error listing sessions: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main execution"""
    if not DynamoDBConfig.is_enabled():
        print("❌ DynamoDB persistence is not enabled!")
        print("Set ENABLE_DYNAMODB_PERSISTENCE=true in .env")
        return
    
    print("\n" + "="*80)
    print("Session Analysis Query Tool")
    print("="*80)
    
    if len(sys.argv) > 1:
        # Query specific session
        session_id = sys.argv[1]
        await query_session(session_id)
    else:
        # List recent sessions
        await list_recent_sessions()
        
        print("\nUsage:")
        print(f"  python {sys.argv[0]} <session_id>  # Query specific session")
        print(f"  python {sys.argv[0]}               # List recent sessions")


if __name__ == '__main__':
    asyncio.run(main())
