# Audio-to-Text WebSocket Server with Reading Assistant

A Python WebSocket server that receives audio content from browser clients, converts it to text using Amazon Transcribe, and provides intelligent reading assistance for children using Amazon Bedrock.

## Features

- **Real-time Audio Processing**: Receives audio chunks from browser clients
- **Amazon Transcribe Integration**: Converts audio to text using AWS streaming transcription
- **Reading Assistant**: Uses Amazon Bedrock (Nova Lite) to detect when children need help
- **Text-to-Speech**: Converts help messages to audio using Amazon Polly (Joanna voice)
- **Intelligent Analysis**: Accumulates transcriptions and analyzes for signs of struggle
- **Live Transcription**: Prints transcribed text in real-time
- **Multiple Client Support**: Handles concurrent connections
- **📊 Audio Timeline Metadata**: Track audio chunks with precise timing and duration
- **🔗 Transcription Association**: Link transcriptions to audio segments with word-level timestamps
- **📈 Reading Analytics**: Calculate reading speed (WPM), confidence scores, and session metrics
- **⏱️ Session Timeline**: Complete timeline of audio, transcriptions, and help events
- **🎯 Context-Aware Help**: Help interventions include timing context and trigger information

## Prerequisites

### AWS Setup
1. **AWS Account**: You need an active AWS account
2. **AWS Credentials**: Configure AWS credentials using one of these methods:
   ```bash
   # Option 1: AWS CLI
   aws configure
   
   # Option 2: Environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   
   # Option 3: AWS credentials file (~/.aws/credentials)
   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   region = us-east-1
   ```

3. **IAM Permissions**: Your AWS user/role needs the following permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "transcribe:StartStreamTranscription"
         ],
         "Resource": "*"
       },
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel"
         ],
         "Resource": "arn:aws:bedrock:*::foundation-model/us.amazon.nova-lite-v1:0"
       },
       {
         "Effect": "Allow",
         "Action": [
           "polly:SynthesizeSpeech"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

### System Requirements
- Python 3.8 or higher
- AWS credentials configured

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Verify AWS credentials:
```bash
aws sts get-caller-identity
```

3. Run the server:
```bash
python app.py
```

The server will start on `localhost:8765` by default.

## 🚀 New: Audio Metadata System

The server now includes a comprehensive metadata system for tracking audio timeline and transcription association:

- **Quick Start**: See [QUICK_START.md](QUICK_START.md) for immediate usage
- **Full Documentation**: See [METADATA_SYSTEM.md](METADATA_SYSTEM.md) for detailed information
- **Test Suite**: Run `python3 test_metadata.py` to verify functionality

### Key Capabilities

1. **Audio Chunk Tracking**: Every audio chunk is tracked with timing, duration, and sequence
2. **Transcription Association**: Transcriptions are linked to audio segments with precise timestamps
3. **Word-Level Timing**: Individual word timestamps when available from Transcribe
4. **Session Metrics**: Automatic calculation of reading speed, confidence, and progress
5. **Timeline API**: Query session timeline and metrics via WebSocket

### Quick Example

```python
# Get session timeline
timeline = audio_buffer_manager.get_session_timeline(client_id)

# Get chunks in time range
chunks = audio_buffer_manager.get_chunks_in_range(client_id, 1000, 5000)

# Access session metrics
session = audio_buffer_manager.get_session(client_id)
print(f"Reading speed: {session.metrics.reading_speed_wpm} WPM")
```

## 📊 Session Analysis & DynamoDB Integration

The server now automatically saves comprehensive session analysis data to DynamoDB:

- **Integration Guide**: See [SESSION_ANALYSIS_INTEGRATION.md](SESSION_ANALYSIS_INTEGRATION.md) for complete documentation
- **Query Tool**: Use `python query_session_analysis.py` to retrieve session data
- **Batch Metrics**: Per-minute reading analysis with miscue detection
- **Session Summaries**: Complete session analysis with insights and recommendations

### Key Features

1. **Real-time Batch Analysis**: Analyze reading performance every 60 seconds
2. **Miscue Detection**: Track omissions, insertions, substitutions, repetitions, and hesitations
3. **Session Summaries**: Comprehensive end-of-session analysis with full transcript
4. **DynamoDB Storage**: All data persisted to AWS DynamoDB for long-term analysis
5. **Query API**: Retrieve complete session data programmatically

### Quick Example

```bash
# List recent sessions
python query_session_analysis.py

# Query specific session with full analysis
python query_session_analysis.py <session_id>
```

```python
# Programmatic access
from dynamodb_persistence import DynamoDBPersistence

dynamodb = DynamoDBPersistence()
data = await dynamodb.get_complete_session_data(session_id)

# Access batch metrics
for batch in data['batch_metrics']:
    print(f"WPM: {batch['words_per_minute']}")
    print(f"Miscues: {batch['miscue_counts']['Total']}")

# Access session summary
summary = data['session_summary']
print(f"Total words: {summary['total_words']}")
print(f"Average WPM: {summary['average_wpm']}")
print(f"Insights: {summary['insights']}")
```

## Configuration

The reading assistant behavior can be configured in `config.py`:

- **ACCUMULATION_WINDOW_SECONDS**: How long to accumulate text before analyzing (default: 10 seconds)
- **BEDROCK_MODEL_ID**: The Bedrock model to use (default: Nova Lite)
- **BEDROCK_TEMPERATURE**: Model temperature for response consistency (default: 0.3)
- **BEDROCK_MAX_TOKENS**: Maximum tokens in Bedrock response (default: 500)

## How It Works

1. **Client Connection**: Browser clients connect via WebSocket
2. **Audio Reception**: Server receives base64-encoded audio chunks
3. **Metadata Tracking**: Audio chunks are tracked with timing and duration metadata
4. **Direct Streaming**: Audio is sent directly to Amazon Transcribe (supports WebM/Opus format)
5. **Transcription**: Amazon Transcribe processes the audio stream with word-level timestamps
6. **Timeline Association**: Transcriptions are linked to audio chunks by time range
7. **Text Accumulation**: Transcribed text is accumulated over configurable time window (10 seconds)
8. **AI Analysis**: Amazon Bedrock analyzes accumulated text for signs of struggle
9. **Help Detection**: If child needs help, generates encouraging assistance message
10. **Context Capture**: Help events include timing context and trigger transcriptions
11. **Text-to-Speech**: Amazon Polly converts help message to natural-sounding audio (MP3)
12. **Audio Playback**: Client receives and plays audio help message to the child
13. **Metrics Calculation**: Session metrics (WPM, confidence, etc.) are calculated in real-time
14. **Text Output**: Transcribed text, metadata, and help messages are sent to client and printed to console

## Audio Processing Pipeline

```
Browser Audio (WebM/Opus) 
    ↓ Base64 Encoding
WebSocket Client 
    ↓ Base64 Decoding
Python Server 
    ↓ Metadata Tracking (AudioBufferManager)
    ↓ Direct Streaming
Amazon Transcribe
    ↓ Real-time Processing + Word Timestamps
Transcribed Text + Metadata
    ↓ Timeline Association
Session Timeline (Audio + Transcriptions + Help Events)
    ↓ Metrics Calculation
Console Output + Client Updates
```

## Client Integration

### Send Audio
Browser clients should send audio data in this JSON format:
```json
{
  "type": "audio",
  "data": "base64_encoded_audio_data_here"
}
```

Or send raw base64 audio data directly as a string.

### Receive Enhanced Transcriptions
```json
{
  "type": "transcription",
  "transcription_id": "uuid",
  "text": "The cat sat on the mat",
  "confidence": 0.95,
  "is_final": true,
  "start_time_ms": 1234,
  "end_time_ms": 2345,
  "session_offset_ms": 5678,
  "word_timestamps": [
    {"word": "The", "start_time_ms": 1234, "end_time_ms": 1300, "confidence": 0.98}
  ],
  "timestamp": "2026-01-14T10:30:00Z"
}
```

### Receive Help Events with Context
```json
{
  "type": "help_needed",
  "needs_help": true,
  "help_message": "Try sounding out the word slowly",
  "audio": "base64_audio_data",
  "confidence": 0.85,
  "reason": "Child struggling with pronunciation",
  "session_time_offset_ms": 12345,
  "trigger_timestamps": [
    "2026-01-14T10:30:00.123Z",
    "2026-01-14T10:30:02.456Z",
    "2026-01-14T10:30:04.789Z"
  ],
  "accumulation_duration_ms": 4666,
  "timestamp": "2026-01-14T10:30:05Z"
}
```

### Request Session Data
```json
// Request timeline
{"type": "get_session_timeline"}

// Request metrics
{"type": "get_session_metrics"}
```

## Troubleshooting

### Common Issues:

1. **AWS Credentials Error**:
   - Ensure AWS credentials are properly configured
   - Check IAM permissions for Transcribe service

2. **Audio Format Issues**:
   - The server tries WebM/Opus format first, then falls back to PCM
   - Ensure your browser is sending compatible audio format
   - Check browser console for audio recording errors

3. **Transcription Not Working**:
   - Verify internet connection
   - Check AWS region settings
   - Ensure audio quality is sufficient (clear speech, minimal background noise)

### Supported Audio Formats:
- **Input**: WebM with Opus codec (from browsers) - preferred
- **Fallback**: PCM format if WebM fails
- **Transcribe**: Supports both Opus and PCM formats

## AWS Costs

Amazon Transcribe Streaming pricing (as of 2024):
- **Pay-per-second** of audio transcribed
- **Minimum charge**: 15 seconds per request
- Check current pricing at: https://aws.amazon.com/transcribe/pricing/

## Server Output Example

```
[2024-01-09 10:30:15] Client connected: 192.168.1.100:54321
[2024-01-09 10:30:16] Initialized Transcribe streaming for 192.168.1.100:54321
[2024-01-09 10:30:17] Sent audio chunk to Transcribe for 192.168.1.100:54321 (3200 bytes)

[TRANSCRIPTION] The cat sat on the mat
[METADATA] Time: 1234-2345ms, Confidence: 0.95

[LLM RESPONSE] Great job! Keep reading.

[SESSION ENDED] 192.168.1.100:54321
Duration: 45.2s
Transcriptions: 15
Help Events: 2
Words: 150
Reading Speed: 85.5 WPM
```

## Project Structure

```
Server/
├── app.py                      # Main WebSocket server with metadata integration
├── config.py                   # Configuration settings
├── models.py                   # Data models for metadata (NEW)
├── audio_buffer_manager.py     # Audio timeline management (NEW)
├── test_metadata.py            # Test suite for metadata system (NEW)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── METADATA_SYSTEM.md          # Detailed metadata documentation (NEW)
└── QUICK_START.md              # Quick start guide for metadata (NEW)
```