# Session Analysis Data Flow

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          BROWSER CLIENT                                  │
│  ┌──────────────┐                                                       │
│  │ Microphone   │ ──► Audio Stream (WebM/Opus)                         │
│  └──────────────┘                                                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ WebSocket
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PYTHON SERVER (app.py)                            │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ AudioBufferManager                                                │  │
│  │  • Store audio chunks with metadata                              │  │
│  │  • Track timing and sequence                                     │  │
│  │  • Calculate session metrics                                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                 │                                        │
│                                 ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Amazon Transcribe Streaming                                       │  │
│  │  • Real-time speech-to-text                                      │  │
│  │  • Word-level timestamps                                         │  │
│  │  • Confidence scores                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                 │                                        │
│                    ┌────────────┴────────────┐                          │
│                    ▼                         ▼                          │
│  ┌─────────────────────────┐   ┌──────────────────────────┐           │
│  │ ReadingAssistant        │   │ BatchAnalyzer            │           │
│  │  • Accumulate text      │   │  • Analyze per minute    │           │
│  │  • Detect struggles     │   │  • Detect miscues        │           │
│  │  • Generate help        │   │  • Calculate WPM         │           │
│  └─────────────────────────┘   └──────────────────────────┘           │
│              │                              │                            │
│              ▼                              ▼                            │
│  ┌─────────────────────────┐   ┌──────────────────────────┐           │
│  │ Amazon Bedrock          │   │ BatchMetrics             │           │
│  │  • AI analysis          │   │  • Word count            │           │
│  │  • Help messages        │   │  • WPM                   │           │
│  └─────────────────────────┘   │  • Miscue counts         │           │
│              │                  │  • Confidence            │           │
│              ▼                  └──────────────────────────┘           │
│  ┌─────────────────────────┐              │                            │
│  │ Amazon Polly            │              │                            │
│  │  • Text-to-speech       │              │                            │
│  │  • Audio response       │              │                            │
│  └─────────────────────────┘              │                            │
│              │                             │                            │
│              └─────────────┬───────────────┘                            │
│                            ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ SessionAnalyzer                                                   │  │
│  │  • Aggregate batch metrics                                       │  │
│  │  • Generate session summary                                      │  │
│  │  • Calculate insights                                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                            │                                            │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    DYNAMODB PERSISTENCE LAYER                            │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ DynamoDBPersistence                                               │  │
│  │  • Async write queue                                             │  │
│  │  • Batch operations                                              │  │
│  │  • Background workers                                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                            │                                            │
│              ┌─────────────┼─────────────┐                             │
│              ▼             ▼             ▼                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│  │ Audio Chunks │ │ Transcripts  │ │ Help Events  │                  │
│  │ (real-time)  │ │ (real-time)  │ │ (real-time)  │                  │
│  └──────────────┘ └──────────────┘ └──────────────┘                  │
│                                                                          │
│  ┌──────────────┐ ┌──────────────────────────────────────────────┐   │
│  │ Batch Metrics│ │ Session Summary                               │   │
│  │ (per minute) │ │ (end of session)                              │   │
│  └──────────────┘ └──────────────────────────────────────────────┘   │
│                                                                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AWS DYNAMODB (reading_sessions)                       │
│                                                                          │
│  Single Table Design:                                                   │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ PK: SESSION#<id>  │  SK: METADATA                              │   │
│  │ PK: SESSION#<id>  │  SK: CHUNK#<time>#<seq>                    │   │
│  │ PK: SESSION#<id>  │  SK: TRANS#<time>#<id>                     │   │
│  │ PK: SESSION#<id>  │  SK: HELP#<time>#<id>                      │   │
│  │ PK: SESSION#<id>  │  SK: BATCH#<time>#<id>  ◄── NEW            │   │
│  │ PK: SESSION#<id>  │  SK: SUMMARY            ◄── NEW            │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Global Secondary Indexes:                                              │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ GSI1: Query by Type and Date                                   │   │
│  │   PK: SESSION | BATCH_METRICS | SESSION_SUMMARY                │   │
│  │   SK: DATE#YYYY-MM-DD#timestamp                                │   │
│  └────────────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ GSI2: Query by Client/Student                                  │   │
│  │   PK: CLIENT#<id> | STUDENT#<id>                               │   │
│  │   SK: DATE#YYYY-MM-DD#timestamp                                │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Persistence Timeline

```
Session Start
    │
    ├─► Session Metadata ──────────────────────► DynamoDB (METADATA)
    │
    ▼
Audio Chunks (continuous)
    │
    ├─► Audio Chunk Metadata ──────────────────► DynamoDB (CHUNK#...)
    │
    ▼
Transcriptions (real-time)
    │
    ├─► Transcription + Timestamps ────────────► DynamoDB (TRANS#...)
    │
    ▼
Every 60 seconds
    │
    ├─► Batch Analysis
    │       • Calculate WPM
    │       • Detect miscues
    │       • Aggregate metrics
    │
    └─► BatchMetrics ──────────────────────────► DynamoDB (BATCH#...)  ◄── NEW
    │
    ▼
Help Events (as needed)
    │
    ├─► AI Analysis + Audio Response ──────────► DynamoDB (HELP#...)
    │
    ▼
Session End
    │
    ├─► Session Analysis
    │       • Aggregate all batches
    │       • Calculate totals
    │       • Generate insights
    │
    └─► SessionSummary ────────────────────────► DynamoDB (SUMMARY)    ◄── NEW
```

## Data Structure in DynamoDB

### Session Metadata
```json
{
  "PK": "SESSION#9800438c-...",
  "SK": "METADATA",
  "Type": "SESSION",
  "ClientId": "192.168.1.100:54321",
  "StartTime": "2026-01-14T13:42:49.167510",
  "EndTime": "2026-01-14T13:44:47.892319",
  "Metrics": {
    "TotalWords": 95,
    "ReadingSpeedWpm": 48.01,
    "AverageConfidence": 0.92
  }
}
```

### Batch Metrics (NEW)
```json
{
  "PK": "SESSION#9800438c-...",
  "SK": "BATCH#2026-01-14T13:43:00#a1b2c3d4-...",
  "Type": "BATCH_METRICS",
  "WordCount": 85,
  "WordsPerMinute": 85.0,
  "MiscueCounts": {
    "Omissions": 2,
    "Insertions": 1,
    "Substitutions": 3,
    "Total": 6
  },
  "Transcriptions": ["text1", "text2", "text3"]
}
```

### Session Summary (NEW)
```json
{
  "PK": "SESSION#9800438c-...",
  "SK": "SUMMARY",
  "Type": "SESSION_SUMMARY",
  "TotalWords": 450,
  "AverageWpm": 75.5,
  "OverallAccuracy": 94.2,
  "TotalMiscueCounts": {
    "Omissions": 8,
    "Insertions": 4,
    "Substitutions": 12,
    "Total": 24
  },
  "FullTranscript": "complete session transcript...",
  "Insights": {
    "reading_speed": "below_grade_level",
    "total_miscues": 24,
    "miscue_rate": 0.053
  }
}
```

## Query Patterns

### 1. Get Complete Session Data
```
Query: PK = "SESSION#<id>"
Returns: All items for session (metadata, chunks, transcripts, batches, summary)
```

### 2. Get All Sessions for a Date
```
Query GSI1: PK = "SESSION", SK begins_with "DATE#2026-01-14"
Returns: All session metadata for that date
```

### 3. Get Student's Sessions
```
Query GSI2: PK = "STUDENT#<id>"
Returns: All sessions for that student
```

### 4. Get Batch Metrics Across Sessions
```
Query GSI1: PK = "BATCH_METRICS", SK begins_with "DATE#2026-01-14"
Returns: All batch metrics for that date
```

## Integration Points

### 1. Real-time (During Session)
- Audio chunks → DynamoDB (batched)
- Transcriptions → DynamoDB (batched)
- Help events → DynamoDB (immediate)

### 2. Per-Minute (Every 60s)
- Batch analysis → BatchMetrics → DynamoDB (immediate)

### 3. End of Session
- Session analysis → SessionSummary → DynamoDB (immediate)
- Update session metadata (end time, final metrics)

## Performance Optimizations

### Write Path
```
Application
    ↓
Async Queue (in-memory)
    ↓
Background Workers (2-4 threads)
    ↓
Batch Write (up to 25 items)
    ↓
DynamoDB
```

### Read Path
```
Query Tool / Application
    ↓
DynamoDB Query (using PK/SK or GSI)
    ↓
Single request for session data
    ↓
Return complete dataset
```

## Monitoring Points

1. **Queue Depths**: Monitor write queue size
2. **Write Latency**: Track time from generation to DynamoDB
3. **Batch Sizes**: Optimize batch sizes for throughput
4. **GSI Usage**: Monitor GSI query patterns
5. **TTL Cleanup**: Track expired items

## Error Handling

```
Write Failure
    ↓
Retry Individual Items
    ↓
Log Error
    ↓
Continue Processing
    (Don't block session)
```

## Future Enhancements

1. **DynamoDB Streams** → Real-time analytics
2. **S3 Integration** → Archive old sessions
3. **Lambda Triggers** → Automated reporting
4. **CloudWatch Metrics** → Performance monitoring
5. **Multi-region** → Global availability
