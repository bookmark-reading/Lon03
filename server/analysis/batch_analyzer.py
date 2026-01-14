"""
Batch Analyzer for real-time per-minute reading analysis
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4
from .reading_engine import ReadingAnalysisEngine
from .analysis_models import BatchMetrics, MiscueEvent, MiscueType


class BatchAnalyzer:
    """
    Analyzes batches of transcriptions in real-time (e.g., per minute).
    Runs analysis on accumulated transcriptions and generates metrics.
    """
    
    def __init__(
        self,
        batch_interval_seconds: int = 60,
        model_id: Optional[str] = None,
        region: Optional[str] = None,
        passage: Optional[str] = None
    ):
        """
        Initialize the Batch Analyzer
        
        Args:
            batch_interval_seconds: How often to analyze batches (default: 60 seconds)
            model_id: AWS Bedrock model ID
            region: AWS region
            passage: Optional expected reading passage for comparison
        """
        self.batch_interval_seconds = batch_interval_seconds
        self.passage = passage
        self.analysis_engine = ReadingAnalysisEngine(model_id=model_id, region=region)
        
        # Batch tracking
        self.current_batch_transcriptions = []
        self.current_batch_start = None
        self.batch_results = []
        
    def add_transcription(self, text: str, timestamp: datetime, confidence: float = 0.0):
        """
        Add a transcription to the current batch
        
        Args:
            text: Transcribed text
            timestamp: When the transcription was created
            confidence: Confidence score from transcription service
        """
        if self.current_batch_start is None:
            self.current_batch_start = timestamp
        
        self.current_batch_transcriptions.append({
            'text': text,
            'timestamp': timestamp,
            'confidence': confidence
        })
    
    def should_analyze_batch(self) -> bool:
        """Check if enough time has passed to analyze current batch"""
        if not self.current_batch_transcriptions:
            return False
        
        if self.current_batch_start is None:
            return False
        
        elapsed = (datetime.now() - self.current_batch_start).total_seconds()
        return elapsed >= self.batch_interval_seconds
    
    async def analyze_current_batch(self, session_id: UUID) -> Optional[BatchMetrics]:
        """
        Analyze the current batch of transcriptions
        
        Args:
            session_id: The session ID this batch belongs to
            
        Returns:
            BatchMetrics with analysis results, or None if no data
        """
        if not self.current_batch_transcriptions:
            return None
        
        try:
            # Combine all transcriptions into one text
            combined_text = " ".join([t['text'] for t in self.current_batch_transcriptions])
            
            # Calculate batch metadata
            batch_end = self.current_batch_transcriptions[-1]['timestamp']
            duration_seconds = (batch_end - self.current_batch_start).total_seconds()
            
            # Calculate average confidence
            avg_confidence = sum(t['confidence'] for t in self.current_batch_transcriptions) / len(self.current_batch_transcriptions)
            
            # Run analysis using the engine
            include_passage = self.passage is not None
            analysis_result = self.analysis_engine.analyze_transcript(
                transcript=combined_text,
                passage=self.passage,
                include_passage_analysis=include_passage
            )
            
            if analysis_result.error:
                print(f"[BATCH ANALYSIS ERROR] {analysis_result.error}")
                return None
            
            # Extract KPIs
            kpis = analysis_result.kpis
            
            # Create batch metrics
            batch_metrics = BatchMetrics(
                batch_id=uuid4(),
                session_id=session_id,
                start_time=self.current_batch_start,
                end_time=batch_end,
                transcriptions=[t['text'] for t in self.current_batch_transcriptions],
                word_count=kpis.get('word_count', kpis.get('words_read', 0)),
                words_per_minute=kpis.get('estimated_wpm', 0.0) if kpis.get('estimated_wpm') else self._calculate_wpm(combined_text, duration_seconds),
                average_confidence=avg_confidence,
                omissions=kpis.get('omissions', 0),
                insertions=kpis.get('insertions', 0),
                substitutions=kpis.get('substitutions', 0),
                repetitions=kpis.get('repetitions', 0),
                self_corrections=kpis.get('self_corrections', 0),
                hesitations=kpis.get('hesitations', 0),
                expected_text=self.passage,
                accuracy_percentage=kpis.get('accuracy_percentage')
            )
            
            # Store result
            self.batch_results.append(batch_metrics)
            
            # Clear current batch
            self.current_batch_transcriptions = []
            self.current_batch_start = None
            
            print(f"[BATCH ANALYSIS] Batch {batch_metrics.batch_id} analyzed: "
                  f"{batch_metrics.word_count} words, {batch_metrics.words_per_minute:.1f} WPM, "
                  f"{kpis.get('omissions', 0)} omissions, {kpis.get('substitutions', 0)} substitutions")
            
            return batch_metrics
            
        except Exception as e:
            print(f"[BATCH ANALYSIS ERROR] {str(e)}")
            return None
    
    def _calculate_wpm(self, text: str, duration_seconds: float) -> float:
        """Calculate words per minute from text and duration"""
        if duration_seconds == 0:
            return 0.0
        
        word_count = len(text.split())
        minutes = duration_seconds / 60.0
        return word_count / minutes if minutes > 0 else 0.0
    
    def get_batch_history(self) -> List[BatchMetrics]:
        """Get all analyzed batch results"""
        return self.batch_results
    
    def reset(self):
        """Reset batch analyzer (e.g., for new session)"""
        self.current_batch_transcriptions = []
        self.current_batch_start = None
        self.batch_results = []
    
    def set_passage(self, passage: Optional[str]):
        """Update the expected reading passage"""
        self.passage = passage
