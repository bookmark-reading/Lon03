import asyncio
import websockets
import json
import base64
import io
import os
import struct
from datetime import datetime
from uuid import uuid4
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import boto3
from config import (
    ACCUMULATION_WINDOW_SECONDS,
    BEDROCK_MODEL_ID,
    READING_ASSISTANT_PROMPT,
    BEDROCK_TEMPERATURE,
    BEDROCK_MAX_TOKENS,
    POLLY_VOICE_ID,
    POLLY_ENGINE,
    POLLY_OUTPUT_FORMAT,
    POLLY_LANGUAGE_CODE
)
from models import (
    AudioChunk,
    Transcription,
    HelpEvent,
    WordTimestamp,
    ReadingSession,
    SessionMetrics
)
from audio_buffer_manager import AudioBufferManager

# DynamoDB imports (optional)
try:
    from dynamodb_persistence import DynamoDBPersistence
    from dynamodb_config import DynamoDBConfig
    DYNAMODB_AVAILABLE = True
except ImportError:
    DYNAMODB_AVAILABLE = False
    print("[WARNING] DynamoDB modules not available. Running without persistence.")
from analysis import BatchAnalyzer, SessionAnalyzer

class ReadingAssistant:
    """Analyzes accumulated transcriptions to detect if child needs help"""
    
    def __init__(self, aws_region, audio_buffer_manager):
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=aws_region)
        self.polly_client = boto3.client('polly', region_name=aws_region)
        self.accumulated_text = []
        self.last_analysis_time = None
        self.audio_buffer_manager = audio_buffer_manager
        
    def add_transcription(self, text, transcription_obj=None):
        """Add a transcription to the accumulation buffer with metadata"""
        current_timestamp = datetime.now()
        
        entry = {
            'text': text,
            'timestamp': current_timestamp,
            'timestamp_iso': current_timestamp.isoformat()
        }
        
        # Add metadata if transcription object provided
        if transcription_obj:
            entry['transcription_id'] = str(transcription_obj.transcription_id)
            entry['start_time_ms'] = transcription_obj.start_time_ms
            entry['end_time_ms'] = transcription_obj.end_time_ms
            entry['session_offset_ms'] = transcription_obj.session_offset_ms
            entry['audio_chunk_ids'] = [str(cid) for cid in transcription_obj.audio_chunk_ids]
            entry['confidence'] = transcription_obj.confidence
            entry['word_count'] = len(text.split())
        
        self.accumulated_text.append(entry)
        
        # Log the accumulation
        print(f"[ACCUMULATED] '{text}' at {entry['timestamp_iso']}")
        
    def get_accumulated_text(self):
        """Get all accumulated text as a single string"""
        return ' '.join([item['text'] for item in self.accumulated_text])
    
    def should_analyze(self):
        """Check if enough time has passed to analyze"""
        if not self.accumulated_text:
            return False
            
        if self.last_analysis_time is None:
            return True
            
        time_since_last = (datetime.now() - self.last_analysis_time).total_seconds()
        return time_since_last >= ACCUMULATION_WINDOW_SECONDS
    
    async def analyze_for_help(self):
        """Analyze accumulated text using Bedrock to detect if child needs help"""
        if not self.accumulated_text:
            return None
            
        accumulated = self.get_accumulated_text()
        
        if not accumulated.strip():
            return None
        
        try:
            # Prepare the prompt for Nova Lite using config
            prompt = READING_ASSISTANT_PROMPT.format(text=accumulated)

            # Call Bedrock Nova Lite using the correct format
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "temperature": BEDROCK_TEMPERATURE,
                    "maxTokens": BEDROCK_MAX_TOKENS
                }
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps(request_body)
            )
            
            # Parse response for Nova model
            response_body = json.loads(response['body'].read())
            response_text = response_body['output']['message']['content'][0]['text']
            
            # Parse JSON response
            result = json.loads(response_text)
            
            # Update analysis time
            self.last_analysis_time = datetime.now()
            
            # Clear accumulated text after analysis
            self.accumulated_text = []
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"[{datetime.now()}] Error parsing Bedrock response: {e}")
            return None
        except Exception as e:
            print(f"[{datetime.now()}] Error analyzing with Bedrock: {e}")
            return None
    
    async def text_to_speech(self, text):
        """Convert text to speech using Amazon Polly"""
        try:
            # Use Amazon Polly to synthesize speech
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat=POLLY_OUTPUT_FORMAT,
                VoiceId=POLLY_VOICE_ID,
                Engine=POLLY_ENGINE,
                LanguageCode=POLLY_LANGUAGE_CODE
            )
            
            # Read the audio stream
            audio_stream = response['AudioStream'].read()
            
            # Convert to base64 for transmission
            audio_base64 = base64.b64encode(audio_stream).decode('utf-8')
            
            return audio_base64
            
        except Exception as e:
            print(f"[{datetime.now()}] Error converting text to speech: {e}")
            return None

class TranscriptHandler(TranscriptResultStreamHandler):
    """Handler for Amazon Transcribe streaming results"""
    
    def __init__(self, transcript_result_stream, client_id, server_instance):
        super().__init__(transcript_result_stream)
        self.client_id = client_id
        self.server_instance = server_instance
    
    async def handle_stream(self):
        """Handle the transcript result stream"""
        try:
            async for event in self._transcript_result_stream:
                await self.handle_transcript_event(event)
        except Exception as e:
            print(f"[{datetime.now()}] Error in transcript stream: {e}")
        
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """Handle transcription results from Amazon Transcribe"""
        results = transcript_event.transcript.results
        
        for result in results:
            # Only process final results
            if not result.is_partial:
                for alt in result.alternatives:
                    transcript = alt.transcript
                    confidence = alt.confidence if hasattr(alt, 'confidence') else 0.0
                    
                    # Extract word-level timestamps if available
                    word_timestamps = []
                    if hasattr(result, 'items'):
                        for item in result.items:
                            if hasattr(item, 'start_time') and hasattr(item, 'end_time'):
                                word_timestamps.append(WordTimestamp(
                                    word=item.content,
                                    start_time_ms=int(float(item.start_time) * 1000),
                                    end_time_ms=int(float(item.end_time) * 1000),
                                    confidence=item.confidence if hasattr(item, 'confidence') else 0.0
                                ))
                    
                    # Get session and calculate timing
                    session = self.server_instance.audio_buffer_manager.get_session(self.client_id)
                    if session:
                        # Calculate start/end times from word timestamps or estimate
                        if word_timestamps:
                            start_time_ms = word_timestamps[0].start_time_ms
                            end_time_ms = word_timestamps[-1].end_time_ms
                        else:
                            # Estimate based on current session time
                            current_time = self.server_instance.audio_buffer_manager.get_current_session_time(self.client_id)
                            # Rough estimate: 150 words per minute = 2.5 words per second
                            word_count = len(transcript.split())
                            estimated_duration_ms = int((word_count / 2.5) * 1000)
                            end_time_ms = current_time
                            start_time_ms = max(0, end_time_ms - estimated_duration_ms)
                        
                        # Get associated audio chunks
                        audio_chunks = self.server_instance.audio_buffer_manager.get_chunks_in_range(
                            self.client_id,
                            start_time_ms,
                            end_time_ms
                        )
                        audio_chunk_ids = [chunk.chunk_id for chunk in audio_chunks]
                        
                        # Create transcription object
                        transcription_obj = Transcription(
                            transcription_id=uuid4(),
                            session_id=session.session_id,
                            audio_chunk_ids=audio_chunk_ids,
                            text=transcript,
                            start_time_ms=start_time_ms,
                            end_time_ms=end_time_ms,
                            session_offset_ms=start_time_ms,
                            confidence=confidence,
                            is_final=True,
                            word_timestamps=word_timestamps,
                            created_at=datetime.now()
                        )
                        
                        # Add to session
                        session.transcriptions.append(transcription_obj)
                        
                        # Persist to DynamoDB if enabled
                        if self.server_instance.dynamodb:
                            await self.server_instance.dynamodb.save_transcription(transcription_obj)
                        
                        # Print transcription
                        print(f"\n[TRANSCRIPTION] {transcript}")
                        print(f"[METADATA] Time: {start_time_ms}-{end_time_ms}ms, Confidence: {confidence:.2f}")
                        
                        # Send final results to client with metadata
                        await self.send_transcription_to_client(
                            self.client_id,
                            transcription_obj
                        )
                        
                        # Add to reading assistant for analysis
                        await self.analyze_for_help(self.client_id, transcription_obj)
                        
                        # Add to batch analyzer for per-minute metrics
                        await self.server_instance.analyze_batch(self.client_id, transcription_obj)

    async def analyze_for_help(self, client_id, transcription_obj):
        """Analyze transcription to detect if child needs help"""
        try:
            # Get or create reading assistant for this client
            if client_id not in self.server_instance.reading_assistants:
                self.server_instance.reading_assistants[client_id] = ReadingAssistant(
                    self.server_instance.aws_region,
                    self.server_instance.audio_buffer_manager
                )
            
            assistant = self.server_instance.reading_assistants[client_id]
            
            # Add transcription to accumulation buffer with metadata
            assistant.add_transcription(transcription_obj.text, transcription_obj)
            
            # Check if it's time to analyze
            if assistant.should_analyze():
                result = await assistant.analyze_for_help()
                
                if result and result.get('needs_help'):
                    await self.send_help_message(client_id, result, transcription_obj)
                        
        except Exception as e:
            print(f"[{datetime.now()}] Error in help analysis: {e}")

    async def send_help_message(self, client_id, analysis_result, transcription_obj):
        """Send help message to client with audio and metadata"""
        try:
            if client_id in self.server_instance.clients:
                websocket = self.server_instance.clients[client_id]
                
                # Get the reading assistant and session
                assistant = self.server_instance.reading_assistants.get(client_id)
                session = self.server_instance.audio_buffer_manager.get_session(client_id)
                
                # Generate audio for the help message
                audio_base64 = None
                help_message = analysis_result.get('help_message', '')
                
                if assistant and help_message:
                    audio_base64 = await assistant.text_to_speech(help_message)
                
                # Print LLM response
                print(f"\n[LLM RESPONSE] {help_message}")
                
                # Create help event with metadata
                if session:
                    # Get trigger transcriptions with timestamps from accumulated text
                    trigger_texts = [item['text'] for item in assistant.accumulated_text]
                    trigger_timestamps = [item['timestamp_iso'] for item in assistant.accumulated_text]
                    
                    # Calculate time range of accumulated text
                    if assistant.accumulated_text:
                        first_timestamp = assistant.accumulated_text[0]['timestamp']
                        last_timestamp = assistant.accumulated_text[-1]['timestamp']
                        accumulation_duration_ms = int((last_timestamp - first_timestamp).total_seconds() * 1000)
                    else:
                        accumulation_duration_ms = 0
                    
                    # Get audio segment IDs
                    audio_segment_ids = []
                    if assistant.accumulated_text:
                        for item in assistant.accumulated_text:
                            if 'audio_chunk_ids' in item:
                                audio_segment_ids.extend([
                                    uuid4() if isinstance(cid, str) else cid 
                                    for cid in item['audio_chunk_ids']
                                ])
                    
                    help_event = HelpEvent(
                        event_id=uuid4(),
                        session_id=session.session_id,
                        session_time_offset_ms=transcription_obj.session_offset_ms,
                        trigger_transcriptions=trigger_texts,
                        trigger_timestamps=trigger_timestamps,
                        accumulation_duration_ms=accumulation_duration_ms,
                        audio_segment_ids=audio_segment_ids,
                        help_message=help_message,
                        audio_response=audio_base64,
                        response_timestamp=datetime.now(),
                        confidence=analysis_result.get('confidence', 0),
                        reason=analysis_result.get('reason', '')
                    )
                    
                    # Add to session
                    session.help_events.append(help_event)
                    
                    # Persist to DynamoDB if enabled
                    if self.server_instance.dynamodb:
                        await self.server_instance.dynamodb.save_help_event(help_event)
                    
                    # Print help event details
                    print(f"[HELP EVENT] Session offset: {transcription_obj.session_offset_ms}ms")
                    print(f"[HELP EVENT] Accumulation duration: {accumulation_duration_ms}ms")
                    print(f"[HELP EVENT] Trigger count: {len(trigger_texts)}")
                
                message = {
                    "type": "help_needed",
                    "needs_help": analysis_result.get('needs_help', False),
                    "help_message": help_message,
                    "audio": audio_base64,
                    "confidence": analysis_result.get('confidence', 0),
                    "reason": analysis_result.get('reason', ''),
                    "timestamp": datetime.now().isoformat(),
                    "session_time_offset_ms": transcription_obj.session_offset_ms if transcription_obj else 0,
                    "trigger_timestamps": trigger_timestamps if assistant else [],
                    "accumulation_duration_ms": accumulation_duration_ms if assistant else 0
                }
                
                await websocket.send(json.dumps(message))
                
        except Exception as e:
            print(f"[{datetime.now()}] Error sending help message: {e}")

    async def send_transcription_to_client(self, client_id, transcription_obj):
        """Send transcription results with metadata back to the client"""
        try:
            if client_id in self.server_instance.clients:
                websocket = self.server_instance.clients[client_id]
                
                message = {
                    "type": "transcription",
                    "transcription_id": str(transcription_obj.transcription_id),
                    "text": transcription_obj.text,
                    "confidence": transcription_obj.confidence,
                    "is_final": transcription_obj.is_final,
                    "start_time_ms": transcription_obj.start_time_ms,
                    "end_time_ms": transcription_obj.end_time_ms,
                    "session_offset_ms": transcription_obj.session_offset_ms,
                    "word_timestamps": [
                        {
                            "word": wt.word,
                            "start_time_ms": wt.start_time_ms,
                            "end_time_ms": wt.end_time_ms,
                            "confidence": wt.confidence
                        }
                        for wt in transcription_obj.word_timestamps
                    ],
                    "timestamp": transcription_obj.created_at.isoformat()
                }
                
                await websocket.send(json.dumps(message))
                
        except Exception as e:
            print(f"[{datetime.now()}] Error sending transcription: {e}")

class AudioWebSocketServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = {}
        self.transcribe_clients = {}
        self.reading_assistants = {}  # One assistant per client
        
        # Initialize DynamoDB persistence if enabled
        self.dynamodb = None
        if DYNAMODB_AVAILABLE and DynamoDBConfig.is_enabled():
            try:
                self.dynamodb = DynamoDBPersistence()
                print(f"[DynamoDB] Persistence enabled")
                print(f"[DynamoDB] Config: {DynamoDBConfig.get_config_summary()}")
            except Exception as e:
                print(f"[DynamoDB] Failed to initialize: {e}")
                print(f"[DynamoDB] Running without persistence")
        else:
            if not DYNAMODB_AVAILABLE:
                print("[DynamoDB] Modules not available")
            else:
                print("[DynamoDB] Persistence disabled (set ENABLE_DYNAMODB_PERSISTENCE=true to enable)")
        
        # Initialize AudioBufferManager with optional DynamoDB
        self.audio_buffer_manager = AudioBufferManager(dynamodb_persistence=self.dynamodb)
        
        # Analysis components
        self.batch_analyzers = {}  # One batch analyzer per client
        self.session_analyzer = None  # Will be initialized when needed
        self.batch_interval_seconds = 60  # Analyze every 60 seconds (1 minute)
        
        # Get AWS region from environment/config
        self.aws_region = self.get_aws_region()
        
        # Check AWS credentials
        self.check_aws_credentials()
        
        # Initialize session analyzer
        self.session_analyzer = SessionAnalyzer(region=self.aws_region)

    def get_aws_region(self):
        """Get AWS region from environment or default to us-east-1"""
        try:
            session = boto3.Session()
            region = session.region_name
            if region:
                print(f"Using AWS region: {region}")
                return region
            else:
                print("No AWS region configured, defaulting to us-east-1")
                print("You can set region using:")
                print("1. AWS CLI: aws configure")
                print("2. Environment variable: export AWS_DEFAULT_REGION=your-region")
                print("3. AWS config file: ~/.aws/config")
                return "us-east-1"
        except Exception as e:
            print(f"Error getting AWS region: {e}")
            print("Defaulting to us-east-1")
            return "us-east-1"

    def check_aws_credentials(self):
        """Check if AWS credentials are configured"""
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials is None:
                print("WARNING: No AWS credentials found!")
                print("Please configure AWS credentials using one of these methods:")
                print("1. AWS CLI: aws configure")
                print("2. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
                print("3. IAM roles (if running on EC2)")
                print("4. AWS credentials file")
            else:
                print(f"AWS credentials found for region: {session.region_name or 'us-east-1 (default)'}")
        except Exception as e:
            print(f"Error checking AWS credentials: {e}")

    async def handle_client(self, websocket, path):
        """Handle incoming WebSocket connections"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients[client_id] = websocket
        
        try:
            async for message in websocket:
                await self.process_message(message, client_id)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[{datetime.now()}] Error: {e}")
        finally:
            await self.cleanup_client(client_id)

    async def cleanup_client(self, client_id):
        """Clean up client resources"""
        if client_id in self.clients:
            del self.clients[client_id]
        
        if client_id in self.transcribe_clients:
            try:
                stream = self.transcribe_clients[client_id]
                await stream.input_stream.end_stream()
                del self.transcribe_clients[client_id]
            except Exception as e:
                print(f"Error stopping transcribe stream for {client_id}: {e}")
        
        if client_id in self.reading_assistants:
            del self.reading_assistants[client_id]
        
        # End session and calculate final metrics
        self.audio_buffer_manager.end_session(client_id)
        
        # Perform end-of-session analysis
        session = self.audio_buffer_manager.get_session(client_id)
        if session:
            print(f"\n[SESSION ENDED] {client_id}")
            print(f"Duration: {session.total_duration_ms / 1000:.1f}s")
            print(f"Transcriptions: {len(session.transcriptions)}")
            print(f"Help Events: {len(session.help_events)}")
            print(f"Words: {session.metrics.total_words}")
            print(f"Reading Speed: {session.metrics.reading_speed_wpm:.1f} WPM")
            
            # Generate comprehensive session analysis
            await self.generate_session_analysis(client_id)
        
        # Clean up batch analyzer
        if client_id in self.batch_analyzers:
            del self.batch_analyzers[client_id]

    async def process_message(self, message, client_id):
        """Process incoming messages from clients"""
        try:
            # Try to parse as JSON first
            data = json.loads(message)
            
            if data.get("type") == "audio":
                audio_data = data.get("data")
                if audio_data:
                    await self.process_audio_chunk(audio_data, client_id)
            
            elif data.get("type") == "get_session_timeline":
                # Client requesting session timeline
                await self.send_session_timeline(client_id)
            
            elif data.get("type") == "get_session_metrics":
                # Client requesting session metrics
                await self.send_session_metrics(client_id)
            
        except json.JSONDecodeError:
            # If not JSON, treat as raw base64 audio data
            await self.process_audio_chunk(message, client_id)

    async def process_audio_chunk(self, base64_audio, client_id):
        """Process audio chunk and send to Amazon Transcribe"""
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(base64_audio)
            
            # Get current encoding and sample rate from transcribe client
            encoding = "pcm"
            sample_rate = 16000
            if client_id in self.transcribe_clients:
                # Try to get from stored config (we'll need to track this)
                encoding = getattr(self, f'_encoding_{client_id}', 'pcm')
                sample_rate = getattr(self, f'_sample_rate_{client_id}', 16000)
            
            # Store audio chunk metadata (without storing actual audio data to save memory)
            chunk = self.audio_buffer_manager.store_chunk(
                client_id=client_id,
                audio_bytes=audio_bytes,
                sample_rate=sample_rate,
                encoding=encoding,
                store_audio_data=False  # Set to True if you need to replay audio later
            )
            
            # Check chunk size - Amazon Transcribe has limits
            max_chunk_size = 32 * 1024  # 32KB limit for safety
            if len(audio_bytes) > max_chunk_size:
                # Split large chunks into smaller pieces
                for i in range(0, len(audio_bytes), max_chunk_size):
                    chunk_part = audio_bytes[i:i + max_chunk_size]
                    await self.send_audio_chunk_to_transcribe(chunk_part, client_id)
            else:
                await self.send_audio_chunk_to_transcribe(audio_bytes, client_id)
            
        except Exception as e:
            print(f"[{datetime.now()}] Error processing audio: {e}")

    async def send_audio_chunk_to_transcribe(self, audio_bytes, client_id):
        """Send a single audio chunk to Amazon Transcribe"""
        try:
            # Initialize transcribe client if not exists
            if client_id not in self.transcribe_clients:
                await self.initialize_transcribe_client(client_id)
            
            # Send audio to Transcribe
            if client_id in self.transcribe_clients:
                stream = self.transcribe_clients[client_id]
                await stream.input_stream.send_audio_event(audio_chunk=audio_bytes)
            
        except Exception as e:
            print(f"[{datetime.now()}] Error sending audio to Transcribe: {e}")
    
    async def send_session_timeline(self, client_id):
        """Send complete session timeline to client"""
        try:
            if client_id in self.clients:
                websocket = self.clients[client_id]
                timeline = self.audio_buffer_manager.get_session_timeline(client_id)
                
                message = {
                    "type": "session_timeline",
                    "timeline": timeline,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(message))
                
        except Exception as e:
            print(f"[{datetime.now()}] Error sending session timeline: {e}")
    
    async def send_session_metrics(self, client_id):
        """Send session metrics to client"""
        try:
            if client_id in self.clients:
                websocket = self.clients[client_id]
                session = self.audio_buffer_manager.get_session(client_id)
                
                if session:
                    # Calculate current metrics
                    self.audio_buffer_manager._calculate_final_metrics(client_id)
                    
                    message = {
                        "type": "session_metrics",
                        "metrics": session.metrics.to_dict(),
                        "session_info": session.to_dict(),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await websocket.send(json.dumps(message))
                
        except Exception as e:
            print(f"[{datetime.now()}] Error sending session metrics: {e}")

    async def initialize_transcribe_client(self, client_id):
        """Initialize Amazon Transcribe streaming client for a client"""
        try:
            # Create transcribe client with configured region
            client = TranscribeStreamingClient(region=self.aws_region)
            
            # Try PCM format first (more reliable)
            stream = await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=16000,  # Standard sample rate
                media_encoding="pcm",        # PCM format
                enable_partial_results_stabilization=True,
                partial_results_stability="medium"
            )
            
            # Store encoding config for this client
            setattr(self, f'_encoding_{client_id}', 'pcm')
            setattr(self, f'_sample_rate_{client_id}', 16000)
            
            # Create transcript handler with the stream and server instance
            handler = TranscriptHandler(stream.output_stream, client_id, self)
            
            # Start handling the stream
            asyncio.create_task(handler.handle_stream())
            
            # Store the stream for sending audio
            self.transcribe_clients[client_id] = stream
            
        except Exception as e:
            print(f"[{datetime.now()}] Error initializing Transcribe: {e}")
            await self.initialize_transcribe_client_opus_fallback(client_id)

    async def initialize_transcribe_client_opus_fallback(self, client_id):
        """Fallback initialization with OGG-Opus format"""
        try:
            # Create transcribe client with configured region
            client = TranscribeStreamingClient(region=self.aws_region)
            
            # Start streaming transcription with OGG-Opus fallback
            stream = await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=48000,  # Browser sample rate
                media_encoding="ogg-opus",   # OGG-Opus format
                enable_partial_results_stabilization=True,
                partial_results_stability="medium"
            )
            
            # Store encoding config for this client
            setattr(self, f'_encoding_{client_id}', 'ogg-opus')
            setattr(self, f'_sample_rate_{client_id}', 48000)
            
            # Create transcript handler with the stream and server instance
            handler = TranscriptHandler(stream.output_stream, client_id, self)
            
            # Start handling the stream
            asyncio.create_task(handler.handle_stream())
            
            # Store the stream for sending audio
            self.transcribe_clients[client_id] = stream
            
        except Exception as e:
            print(f"[{datetime.now()}] Error initializing Transcribe fallback: {e}")

    async def analyze_batch(self, client_id, transcription_obj):
        """Analyze transcription batch for per-minute metrics"""
        try:
            # Get or create batch analyzer for this client
            if client_id not in self.batch_analyzers:
                self.batch_analyzers[client_id] = BatchAnalyzer(
                    batch_interval_seconds=self.batch_interval_seconds,
                    region=self.aws_region,
                    passage=None  # Can be set later if passage is provided
                )
            
            batch_analyzer = self.batch_analyzers[client_id]
            
            # Add transcription to current batch
            batch_analyzer.add_transcription(
                text=transcription_obj.text,
                timestamp=transcription_obj.created_at,
                confidence=transcription_obj.confidence
            )
            
            # Check if it's time to analyze the batch
            if batch_analyzer.should_analyze_batch():
                session = self.audio_buffer_manager.get_session(client_id)
                if session:
                    batch_metrics = await batch_analyzer.analyze_current_batch(session.session_id)
                    
                    if batch_metrics:
                        # Send batch analysis results to client
                        await self.send_batch_analysis(client_id, batch_metrics)
        
        except Exception as e:
            print(f"[{datetime.now()}] Error in batch analysis: {e}")
    
    async def send_batch_analysis(self, client_id, batch_metrics):
        """Send batch analysis results to client"""
        try:
            if client_id in self.clients:
                websocket = self.clients[client_id]
                
                message = {
                    "type": "batch_analysis",
                    "batch_metrics": batch_metrics.to_dict(),
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(message))
                
                # Persist batch metrics to DynamoDB if enabled
                if self.dynamodb:
                    await self.dynamodb.save_batch_metrics(batch_metrics)
                
                # Print detailed batch analysis to console
                print(f"\n{'='*60}")
                print(f"[BATCH ANALYSIS] Batch {str(batch_metrics.batch_id)[:8]}...")
                print(f"{'='*60}")
                print(f"Time Range: {batch_metrics.start_time.strftime('%H:%M:%S')} - {batch_metrics.end_time.strftime('%H:%M:%S')}")
                print(f"Duration: {(batch_metrics.end_time - batch_metrics.start_time).total_seconds():.1f}s")
                print(f"\nReading Metrics:")
                print(f"  Words: {batch_metrics.word_count}")
                print(f"  WPM: {batch_metrics.words_per_minute:.1f}")
                print(f"  Confidence: {batch_metrics.average_confidence:.1%}")
                if batch_metrics.accuracy_percentage is not None:
                    print(f"  Accuracy: {batch_metrics.accuracy_percentage:.1f}%")
                
                total_miscues = (batch_metrics.omissions + batch_metrics.insertions + 
                               batch_metrics.substitutions + batch_metrics.repetitions + 
                               batch_metrics.hesitations)
                print(f"\nMiscue Analysis:")
                print(f"  Omissions: {batch_metrics.omissions}")
                print(f"  Insertions: {batch_metrics.insertions}")
                print(f"  Substitutions: {batch_metrics.substitutions}")
                print(f"  Repetitions: {batch_metrics.repetitions}")
                print(f"  Hesitations: {batch_metrics.hesitations}")
                print(f"  Total Miscues: {total_miscues}")
                
                if batch_metrics.transcriptions:
                    print(f"\nTranscript:")
                    for i, trans in enumerate(batch_metrics.transcriptions, 1):
                        print(f"  {i}. {trans}")
                
                print(f"{'='*60}\n")
                
        except Exception as e:
            print(f"[{datetime.now()}] Error sending batch analysis: {e}")
    
    async def generate_session_analysis(self, client_id):
        """Generate comprehensive end-of-session analysis"""
        try:
            session = self.audio_buffer_manager.get_session(client_id)
            if not session:
                return
            
            # Get batch results if available
            batch_metrics = []
            if client_id in self.batch_analyzers:
                batch_metrics = self.batch_analyzers[client_id].get_batch_history()
            
            # Get all transcription texts
            transcriptions = [t.text for t in session.transcriptions]
            
            # Generate session summary using session analyzer
            if self.session_analyzer:
                session_summary = await self.session_analyzer.analyze_session(
                    session_id=session.session_id,
                    start_time=session.start_time,
                    end_time=session.end_time or datetime.now(),
                    transcriptions=transcriptions,
                    batch_metrics=batch_metrics,
                    passage=None  # Can be set if passage is provided
                )
                
                # Send session summary to client (if still connected)
                if client_id in self.clients:
                    await self.send_session_summary(client_id, session_summary)
                else:
                    # Log it even if client disconnected
                    print(f"\\n[SESSION SUMMARY]")
                    print(f"Session ID: {session_summary.session_id}")
                    print(f"Total words: {session_summary.total_words}")
                    print(f"Average WPM: {session_summary.average_wpm:.1f}")
                    print(f"Total miscues: {session_summary.total_omissions + session_summary.total_insertions + session_summary.total_substitutions + session_summary.total_repetitions + session_summary.total_hesitations}")
                    
                    # Save to file for later retrieval
                    self.save_session_summary_to_file(session_summary)
        
        except Exception as e:
            print(f"[{datetime.now()}] Error generating session analysis: {e}")
    
    async def send_session_summary(self, client_id, session_summary):
        """Send session summary to client"""
        try:
            if client_id in self.clients:
                websocket = self.clients[client_id]
                
                message = {
                    "type": "session_summary",
                    "summary": session_summary.to_dict(),
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(message))
                
                print(f"\\n[SESSION SUMMARY SENT]")
                print(f"Total words: {session_summary.total_words}")
                print(f"Average WPM: {session_summary.average_wpm:.1f}")
                if session_summary.overall_accuracy:
                    print(f"Accuracy: {session_summary.overall_accuracy:.1f}%")
            
            # Persist session summary to DynamoDB (even if client disconnected)
            if self.dynamodb:
                await self.dynamodb.save_session_summary(session_summary)
                
        except Exception as e:
            print(f"[{datetime.now()}] Error sending session summary: {e}")
    
    def save_session_summary_to_file(self, session_summary):
        """Save session summary to local file"""
        try:
            import os
            
            # Create sessions directory if it doesn't exist
            sessions_dir = os.path.join(os.path.dirname(__file__), 'sessions')
            os.makedirs(sessions_dir, exist_ok=True)
            
            # Save as JSON file
            filename = f"session_{session_summary.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(sessions_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(session_summary.to_dict(), f, indent=2)
            
            print(f"[SESSION SAVED] {filepath}")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error saving session summary: {e}")
    
    def set_passage_for_client(self, client_id, passage):
        """Set the expected reading passage for a client"""
        if client_id in self.batch_analyzers:
            self.batch_analyzers[client_id].set_passage(passage)

    async def start_server(self):
        """Start the WebSocket server"""
        print(f"Starting Audio-to-Text WebSocket server on {self.host}:{self.port}")
        print("Server will:")
        print("1. Receive audio chunks from browser clients")
        print("2. Stream audio directly to Amazon Transcribe")
        print("3. Print transcribed text to console")
        print("4. Analyze reading patterns per minute")
        print("5. Generate session summaries with miscue analysis")
        print("\nNOTE: Audio format compatibility depends on browser and Transcribe support")
        print("If transcription doesn't work, the client may need to send PCM format")
        print("\nWaiting for connections...")
        
        # Start DynamoDB workers if enabled
        if self.dynamodb:
            print("[DynamoDB] Starting background workers...")
            asyncio.create_task(self.dynamodb.start_write_worker())
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever

if __name__ == "__main__":
    server = AudioWebSocketServer()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        # Stop DynamoDB workers if running
        if server.dynamodb:
            print("[DynamoDB] Stopping workers...")
            asyncio.run(server.dynamodb.stop_workers())