"""
Core reading analysis engine using AWS Bedrock
Adapted from analyse_test/reading_agent.py for server integration
"""

import boto3
import json
import re
from typing import Optional, Dict
from langchain_aws import ChatBedrock
from .analysis_models import AnalysisResult


class ReadingAnalysisEngine:
    """
    Core engine for analyzing reading transcripts using AWS Bedrock.
    Uses LangChain and Claude for miscue detection and KPI calculation.
    """
    
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize the Reading Analysis Engine
        
        Args:
            model_id: AWS Bedrock model ID (defaults to Claude 3.5 Sonnet)
            region: AWS region
        """
        self.model_id = model_id or "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.region = region or "us-west-2"
        
        # Initialize AWS Bedrock client
        self.bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=self.region
        )
        
        # Initialize LangChain ChatBedrock
        self.llm = ChatBedrock(
            model_id=self.model_id,
            client=self.bedrock_client,
            model_kwargs={
                "temperature": 0.0,
                "max_tokens": 4096
            }
        )
    
    def analyze_transcript(
        self,
        transcript: str,
        passage: Optional[str] = None,
        include_passage_analysis: bool = False
    ) -> AnalysisResult:
        """
        Analyze a transcript for reading miscues and patterns
        
        Args:
            transcript: The spoken transcript text
            passage: Optional expected passage text for comparison
            include_passage_analysis: Whether to do detailed passage comparison
            
        Returns:
            AnalysisResult with KPIs and miscue detection
        """
        try:
            if include_passage_analysis and passage:
                # Full analysis with passage comparison
                prompt = self._create_passage_comparison_prompt(passage, transcript)
            else:
                # Quick analysis without passage (for real-time batches)
                prompt = self._create_quick_analysis_prompt(transcript)
            
            # Call the LLM
            response = self.llm.invoke(prompt)
            result_text = response.content
            
            # Parse the JSON response
            parsed_result = self._parse_llm_response(result_text)
            
            return AnalysisResult(
                cleaned_passage=parsed_result.get("cleaned_passage"),
                kpis=parsed_result.get("kpis", {}),
                raw_response=result_text,
                error=None
            )
            
        except Exception as e:
            return AnalysisResult(
                error=f"Analysis failed: {str(e)}"
            )
    
    def _create_quick_analysis_prompt(self, transcript: str) -> str:
        """Create prompt for quick transcript analysis without passage"""
        
        prompt = f"""You are an AI reading assessment assistant. Analyze this reading transcript and identify patterns that indicate reading difficulties.

Analyze for:
1. **Repetitions**: Words or phrases repeated multiple times
2. **Hesitations**: Pauses, fillers (um, uh, er), or drawn-out sounds
3. **Self-corrections**: When reader corrects themselves
4. **Fluency issues**: Choppy reading, excessive pauses

Calculate basic metrics:
- Word count
- Estimated words per minute (if timing patterns are evident)
- Fluency score (0-100, where 100 is perfectly fluent)

**TRANSCRIPT:**
{transcript}

Return your analysis as JSON:
```json
{{
    "kpis": {{
        "word_count": <number>,
        "repetitions": <count>,
        "hesitations": <count>,
        "self_corrections": <count>,
        "fluency_score": <0-100>,
        "estimated_wpm": <number or null>
    }},
    "patterns": {{
        "repeated_words": [<list of words repeated>],
        "hesitation_markers": [<list of hesitation sounds/words>],
        "notes": "<brief observations>"
    }}
}}
```"""
        
        return prompt
    
    def _create_passage_comparison_prompt(self, passage: str, transcript: str) -> str:
        """Create prompt for full passage comparison analysis"""
        
        prompt = f"""You are an AI reading assessment assistant. Analyze the following reading session transcript between a Reader (student) and compare it to the given passage text.

Your task is to:
1. Identify all reading miscues and events:
   - **Omissions**: Words in the passage that the reader skipped/didn't read
   - **Insertions**: Extra words the reader added that aren't in the passage
   - **Substitutions**: Words the reader misread (said a different word)
   - **Repetitions**: Words or phrases the reader repeated
   - **Self-corrections**: Errors the reader corrected by themselves
   - **Hesitations**: Pauses, fillers (um, uh), or drawn-out sounds indicating difficulty

2. Create a cleaned passage with inline tags marking each event:
   - [omission] - for skipped words
   - [insertion: word] - for extra words added
   - [substitution: wrong->correct] - for misread words
   - [repeats] - for repeated words
   - [self-correction] - for self-corrected errors
   - [hesitation] - for pauses or fillers

3. Calculate KPIs:
   - Count of each miscue type
   - Words per minute (estimate based on content length)
   - Accuracy percentage (words read correctly / total words * 100)
   - Fluency score (0-100)

**PASSAGE:**
{passage}

**TRANSCRIPT:**
{transcript}

Return your analysis as JSON:
```json
{{
    "cleaned_passage": "<passage with inline [tags]>",
    "kpis": {{
        "total_words": <number>,
        "words_read": <number>,
        "omissions": <count>,
        "insertions": <count>,
        "substitutions": <count>,
        "repetitions": <count>,
        "self_corrections": <count>,
        "hesitations": <count>,
        "accuracy_percentage": <0-100>,
        "fluency_score": <0-100>,
        "estimated_wpm": <number>
    }}
}}
```"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """Parse JSON from LLM response"""
        try:
            # Find JSON in the response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON object directly
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end].strip()
            
            # Parse JSON
            result = json.loads(json_text)
            return result
            
        except Exception as e:
            # If parsing fails, return error in structured format
            return {
                "kpis": {},
                "error": f"Failed to parse LLM response: {str(e)}"
            }
