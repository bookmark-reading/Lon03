# Reading Analysis Module

This module provides real-time and end-of-session analysis for reading sessions, detecting miscues and calculating reading performance metrics.

## Overview

The analysis module is integrated into the server to provide two levels of analysis:

1. **Batch Analysis** (Real-time, per-minute): Analyzes transcriptions every 60 seconds to provide ongoing metrics
2. **Session Analysis** (End-of-session): Comprehensive analysis when the session ends with detailed insights

## Architecture

```
server/analysis/
├── __init__.py                 # Module exports
├── analysis_models.py          # Data models for analysis results
├── reading_engine.py           # Core LLM-based analysis engine
├── batch_analyzer.py           # Real-time per-minute batch analyzer
└── session_analyzer.py         # End-of-session comprehensive analyzer
```

## Components

### 1. Analysis Models (`analysis_models.py`)

**MiscueType**: Enumeration of reading miscue types
- Omission
- Insertion
- Substitution
- Repetition
- Self-correction
- Hesitation

**MiscueEvent**: Individual miscue event with details

**BatchMetrics**: Per-minute metrics including:
- Word count and WPM
- Miscue counts by type
- Average confidence
- Accuracy percentage (if passage provided)

**SessionSummary**: Complete session analysis with:
- Overall statistics
- All batch metrics
- Insights and recommendations
- Full transcript

### 2. Reading Engine (`reading_engine.py`)

Core analysis engine using AWS Bedrock (Claude 3.5 Sonnet):
- Quick analysis for real-time batches
- Comprehensive passage comparison
- JSON-based structured output

### 3. Batch Analyzer (`batch_analyzer.py`)

Manages real-time per-minute analysis:
- Accumulates transcriptions over configurable interval (default: 60s)
- Triggers analysis when interval elapsed
- Sends batch metrics to client via WebSocket
- Stores batch history for session summary

### 4. Session Analyzer (`session_analyzer.py`)

Generates end-of-session comprehensive analysis:
- Aggregates all batch metrics
- Calculates overall statistics
- Generates insights and recommendations
- Saves results to local JSON files

## Integration with Server

### Server Initialization

```python
# In AudioWebSocketServer.__init__()
self.batch_analyzers = {}  # One per client
self.session_analyzer = SessionAnalyzer(region=self.aws_region)
self.batch_interval_seconds = 60  # Per-minute analysis
```

### Real-time Batch Analysis

When a transcription is received:
```python
# In TranscriptHandler.handle_transcript_event()
await self.server_instance.analyze_batch(client_id, transcription_obj)
```

The `analyze_batch()` method:
1. Creates batch analyzer if needed
2. Adds transcription to current batch
3. Checks if interval elapsed
4. Runs analysis and sends results to client

### End-of-Session Analysis

When client disconnects:
```python
# In AudioWebSocketServer.cleanup_client()
await self.generate_session_analysis(client_id)
```

The `generate_session_analysis()` method:
1. Collects all batch metrics
2. Runs comprehensive session analysis
3. Sends summary to client (if connected)
4. Saves to `sessions/` directory as JSON

## WebSocket Messages

### Batch Analysis (Real-time)
```json
{
  "type": "batch_analysis",
  "batch_metrics": {
    "batch_id": "uuid",
    "start_time": "2025-01-14T10:00:00",
    "end_time": "2025-01-14T10:01:00",
    "word_count": 45,
    "words_per_minute": 45.0,
    "miscue_counts": {
      "omissions": 2,
      "insertions": 1,
      "substitutions": 3,
      "repetitions": 1,
      "hesitations": 2,
      "total": 9
    },
    "accuracy_percentage": 92.0
  }
}
```

### Session Summary (End-of-session)
```json
{
  "type": "session_summary",
  "summary": {
    "session_id": "uuid",
    "total_words": 450,
    "average_wpm": 75.0,
    "overall_accuracy": 93.5,
    "total_miscue_counts": {
      "omissions": 12,
      "insertions": 5,
      "substitutions": 15,
      "total": 45
    },
    "insights": {
      "reading_speed": "on_grade_level",
      "accuracy_level": "good",
      "dominant_miscue_type": "substitutions",
      "recommendation": "Practice phonics and word recognition"
    }
  }
}
```

## Configuration

### Batch Interval
Change the analysis frequency:
```python
server = AudioWebSocketServer()
server.batch_interval_seconds = 30  # Analyze every 30 seconds
```

### Reading Passage
Set an expected reading passage for accuracy calculation:
```python
server.set_passage_for_client(client_id, "The cat sat on the mat...")
```

## Local Storage

Session summaries are automatically saved to:
```
server/sessions/session_{session_id}_{timestamp}.json
```

Each file contains the complete `SessionSummary` as JSON for later analysis.

## AWS Requirements

The analysis module requires:
- AWS Bedrock access with Claude 3.5 Sonnet model
- Appropriate IAM permissions for bedrock-runtime
- Configured AWS credentials and region

## Dependencies

```
langgraph>=0.2.0
langchain-core>=0.1.0
langchain-aws>=0.1.0
boto3>=1.34.0
pydantic>=2.0.0
```

## Future Enhancements

- DynamoDB integration for persistent storage
- Passage upload/management via WebSocket
- Real-time passage tracking (word-by-word)
- Custom analysis intervals per client
- Historical trend analysis across sessions
- Export to PDF reports

## Example Usage

```python
# Server automatically handles analysis
# Client just needs to connect and send audio

# Optional: Set reading passage
server.set_passage_for_client(client_id, passage_text)

# Client receives:
# 1. Batch analysis every minute
# 2. Session summary at end
```

## Troubleshooting

**No batch analysis results:**
- Check that transcriptions are being received
- Verify batch interval has elapsed (default 60s)
- Check AWS Bedrock permissions

**Session summary not generated:**
- Verify session ended properly (cleanup_client called)
- Check session_analyzer initialized
- Verify sessions/ directory is writable

**Analysis errors:**
- Check AWS credentials and region
- Verify Bedrock model access (Claude 3.5 Sonnet)
- Check network connectivity to AWS
