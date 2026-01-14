"""
Session Analyzer for end-of-session comprehensive analysis
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from .reading_engine import ReadingAnalysisEngine
from .analysis_models import SessionSummary, BatchMetrics, MiscueEvent, MiscueType


class SessionAnalyzer:
    """
    Analyzes complete reading sessions to generate comprehensive summaries.
    Aggregates batch results and performs full session analysis.
    """
    
    def __init__(
        self,
        model_id: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize the Session Analyzer
        
        Args:
            model_id: AWS Bedrock model ID
            region: AWS region
        """
        self.analysis_engine = ReadingAnalysisEngine(model_id=model_id, region=region)
    
    async def analyze_session(
        self,
        session_id: UUID,
        start_time: datetime,
        end_time: datetime,
        transcriptions: List[str],
        batch_metrics: List[BatchMetrics],
        passage: Optional[str] = None
    ) -> SessionSummary:
        """
        Perform comprehensive end-of-session analysis
        
        Args:
            session_id: Session identifier
            start_time: Session start time
            end_time: Session end time
            transcriptions: All transcription texts from the session
            batch_metrics: List of batch analysis results
            passage: Optional expected reading passage
            
        Returns:
            SessionSummary with comprehensive analysis
        """
        try:
            # Combine all transcriptions
            full_transcript = " ".join(transcriptions)
            
            # Calculate time metrics
            total_duration = (end_time - start_time).total_seconds()
            total_minutes = total_duration / 60.0
            
            # Aggregate batch metrics
            total_words = sum(batch.word_count for batch in batch_metrics) if batch_metrics else len(full_transcript.split())
            
            # Calculate average WPM
            average_wpm = total_words / total_minutes if total_minutes > 0 else 0.0
            
            # Aggregate miscue counts
            total_omissions = sum(batch.omissions for batch in batch_metrics)
            total_insertions = sum(batch.insertions for batch in batch_metrics)
            total_substitutions = sum(batch.substitutions for batch in batch_metrics)
            total_repetitions = sum(batch.repetitions for batch in batch_metrics)
            total_self_corrections = sum(batch.self_corrections for batch in batch_metrics)
            total_hesitations = sum(batch.hesitations for batch in batch_metrics)
            
            # Calculate average confidence
            confidences = [batch.average_confidence for batch in batch_metrics if batch.average_confidence > 0]
            average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Calculate overall accuracy if passage provided
            overall_accuracy = None
            if passage and batch_metrics:
                accuracies = [batch.accuracy_percentage for batch in batch_metrics if batch.accuracy_percentage is not None]
                overall_accuracy = sum(accuracies) / len(accuracies) if accuracies else None
            
            # If passage provided, do comprehensive final analysis
            if passage:
                final_analysis = self.analysis_engine.analyze_transcript(
                    transcript=full_transcript,
                    passage=passage,
                    include_passage_analysis=True
                )
                
                if not final_analysis.error and final_analysis.kpis:
                    # Update metrics with comprehensive analysis
                    kpis = final_analysis.kpis
                    overall_accuracy = kpis.get('accuracy_percentage', overall_accuracy)
            else:
                final_analysis = None
            
            # Generate insights
            insights = self._generate_insights(
                total_words=total_words,
                average_wpm=average_wpm,
                total_omissions=total_omissions,
                total_insertions=total_insertions,
                total_substitutions=total_substitutions,
                total_repetitions=total_repetitions,
                total_self_corrections=total_self_corrections,
                total_hesitations=total_hesitations,
                overall_accuracy=overall_accuracy,
                batch_count=len(batch_metrics)
            )
            
            # Create session summary
            summary = SessionSummary(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                total_words=total_words,
                total_reading_time_minutes=total_minutes,
                average_wpm=average_wpm,
                overall_accuracy=overall_accuracy,
                average_confidence=average_confidence,
                total_omissions=total_omissions,
                total_insertions=total_insertions,
                total_substitutions=total_substitutions,
                total_repetitions=total_repetitions,
                total_self_corrections=total_self_corrections,
                total_hesitations=total_hesitations,
                batch_metrics=batch_metrics,
                full_transcript=full_transcript,
                expected_passage=passage,
                insights=insights
            )
            
            print(f"[SESSION ANALYSIS] Session {session_id} analyzed:")
            print(f"  - Duration: {total_minutes:.1f} minutes")
            print(f"  - Total words: {total_words}")
            print(f"  - Average WPM: {average_wpm:.1f}")
            print(f"  - Total miscues: {total_omissions + total_insertions + total_substitutions + total_repetitions + total_hesitations}")
            if overall_accuracy:
                print(f"  - Overall accuracy: {overall_accuracy:.1f}%")
            
            return summary
            
        except Exception as e:
            print(f"[SESSION ANALYSIS ERROR] {str(e)}")
            
            # Return basic summary on error
            return SessionSummary(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                total_words=len(full_transcript.split()),
                total_reading_time_minutes=(end_time - start_time).total_seconds() / 60.0,
                full_transcript=full_transcript,
                expected_passage=passage,
                insights={'error': str(e)}
            )
    
    def _generate_insights(
        self,
        total_words: int,
        average_wpm: float,
        total_omissions: int,
        total_insertions: int,
        total_substitutions: int,
        total_repetitions: int,
        total_self_corrections: int,
        total_hesitations: int,
        overall_accuracy: Optional[float],
        batch_count: int
    ) -> dict:
        """Generate insights based on session metrics"""
        
        insights = {}
        
        # Reading speed assessment
        if average_wpm < 60:
            insights['reading_speed'] = 'below_grade_level'
            insights['reading_speed_note'] = f'Reading speed of {average_wpm:.0f} WPM is below typical range (60-150 WPM)'
        elif average_wpm > 150:
            insights['reading_speed'] = 'above_grade_level'
            insights['reading_speed_note'] = f'Reading speed of {average_wpm:.0f} WPM is above typical range'
        else:
            insights['reading_speed'] = 'on_grade_level'
            insights['reading_speed_note'] = f'Reading speed of {average_wpm:.0f} WPM is within typical range'
        
        # Accuracy assessment
        if overall_accuracy is not None:
            if overall_accuracy >= 95:
                insights['accuracy_level'] = 'excellent'
                insights['accuracy_note'] = f'Accuracy of {overall_accuracy:.0f}% indicates strong reading comprehension'
            elif overall_accuracy >= 85:
                insights['accuracy_level'] = 'good'
                insights['accuracy_note'] = f'Accuracy of {overall_accuracy:.0f}% indicates good reading comprehension with room for improvement'
            else:
                insights['accuracy_level'] = 'needs_improvement'
                insights['accuracy_note'] = f'Accuracy of {overall_accuracy:.0f}% suggests need for additional practice and support'
        
        # Miscue pattern analysis
        total_miscues = total_omissions + total_insertions + total_substitutions + total_repetitions + total_hesitations
        if total_miscues > 0:
            # Identify dominant miscue type
            miscue_breakdown = {
                'omissions': total_omissions,
                'insertions': total_insertions,
                'substitutions': total_substitutions,
                'repetitions': total_repetitions,
                'hesitations': total_hesitations
            }
            dominant_miscue = max(miscue_breakdown, key=miscue_breakdown.get)
            insights['dominant_miscue_type'] = dominant_miscue
            insights['dominant_miscue_count'] = miscue_breakdown[dominant_miscue]
            
            # Provide recommendations based on dominant miscue
            if dominant_miscue == 'omissions':
                insights['recommendation'] = 'Focus on slowing down and tracking words with finger or pointer'
            elif dominant_miscue == 'substitutions':
                insights['recommendation'] = 'Practice phonics and word recognition strategies'
            elif dominant_miscue == 'repetitions':
                insights['recommendation'] = 'Work on confidence and fluency through repeated reading'
            elif dominant_miscue == 'hesitations':
                insights['recommendation'] = 'Build sight word vocabulary and practice familiar texts'
        
        # Self-correction rate (positive indicator)
        if total_self_corrections > 0:
            correction_rate = (total_self_corrections / total_miscues * 100) if total_miscues > 0 else 0
            insights['self_correction_rate'] = correction_rate
            if correction_rate > 50:
                insights['self_monitoring'] = 'The student demonstrates good self-monitoring skills'
            else:
                insights['self_monitoring'] = 'Encourage the student to self-monitor and self-correct more actively'
        
        # Overall assessment
        insights['total_miscues'] = total_miscues
        insights['total_words'] = total_words
        insights['miscue_rate'] = (total_miscues / total_words * 100) if total_words > 0 else 0
        insights['batches_analyzed'] = batch_count
        
        return insights
