"""
Reading Transcript Analysis Agent using LangGraph
Analyzes reading sessions to identify miscues and calculate KPIs
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
import boto3
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ReadingState(TypedDict):
    """State for the reading analysis workflow"""
    passage: str
    transcript: str
    cleaned_passage: Optional[str]
    kpis: Optional[dict]
    analysis_result: Optional[str]
    error: Optional[str]


class ReadingAnalysisAgent:
    """
    LangGraph agent for analyzing reading transcripts against passages.
    Identifies reading miscues and calculates performance KPIs.
    """
    
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize the Reading Analysis Agent
        
        Args:
            model_id: AWS Bedrock model ID (defaults to Claude 3.5 Sonnet v2 inference profile)
            region: AWS region (defaults to us-west-2)
        """
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID", 
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        
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
        
        # Build the LangGraph workflow
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for reading analysis"""
        
        # Create the graph
        workflow = StateGraph(ReadingState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("analyze_transcript", self._analyze_transcript)
        workflow.add_node("parse_results", self._parse_results)
        
        # Define the flow
        workflow.set_entry_point("validate_input")
        
        # Add conditional edge from validate to either analyze or end
        def should_continue(state: ReadingState) -> str:
            if state.get("error"):
                return "end"
            return "analyze"
        
        workflow.add_conditional_edges(
            "validate_input",
            should_continue,
            {
                "analyze": "analyze_transcript",
                "end": END
            }
        )
        
        workflow.add_edge("analyze_transcript", "parse_results")
        workflow.add_edge("parse_results", END)
        
        # Compile the graph
        return workflow.compile()
    
    def _validate_input(self, state: ReadingState) -> ReadingState:
        """Validate input passage and transcript"""
        if not state.get("passage") or not state.get("transcript"):
            state["error"] = "Both passage and transcript are required"
            return state
        
        if not isinstance(state["passage"], str) or not isinstance(state["transcript"], str):
            state["error"] = "Passage and transcript must be strings"
            return state
        
        return state
    
    def _analyze_transcript(self, state: ReadingState) -> ReadingState:
        """Use LLM to analyze the transcript against the passage"""
        
        if state.get("error"):
            return state
        
        prompt = self._create_analysis_prompt(state["passage"], state["transcript"])
        
        try:
            # Call the LLM
            response = self.llm.invoke(prompt)
            state["analysis_result"] = response.content
        except Exception as e:
            state["error"] = f"LLM analysis failed: {str(e)}"
        
        return state
    
    def _parse_results(self, state: ReadingState) -> ReadingState:
        """Parse the LLM response and extract cleaned passage and KPIs"""
        
        if state.get("error"):
            return state
        
        try:
            # Extract JSON from the response
            result_text = state["analysis_result"]
            
            # Find JSON in the response (handle markdown code blocks)
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                json_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.find("```", json_start)
                json_text = result_text[json_start:json_end].strip()
            else:
                # Try to find JSON object directly
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                json_text = result_text[json_start:json_end].strip()
            
            # Parse JSON
            result = json.loads(json_text)
            
            state["cleaned_passage"] = result.get("cleaned_passage", "")
            state["kpis"] = result.get("kpis", {})
            
        except Exception as e:
            state["error"] = f"Failed to parse results: {str(e)}"
        
        return state
    
    def _create_analysis_prompt(self, passage: str, transcript: str) -> str:
        """Create the prompt for the LLM to analyze the reading session"""
        
        prompt = f"""You are an AI reading assessment assistant. Analyze the following reading session transcript between a Reader (student) and a Tutor (agent), and compare it to the given passage text.

Your task is to:
1. Identify all reading miscues and events:
   - **Omissions**: Words in the passage that the reader skipped/didn't read
   - **Insertions**: Extra words the reader added that aren't in the passage
   - **Substitutions**: Words the reader misread (said a different word)
   - **Repetitions**: Words or phrases the reader repeated
   - **Self-corrections**: Errors the reader corrected by themselves
   - **Hesitations**: Pauses, fillers (um, uh), or drawn-out sounds indicating difficulty
   - **Questions**: Questions the reader asked for help
   - **Agent interventions**: Times the tutor had to provide help or the correct word

2. Create a cleaned passage with inline tags marking each event:
   - [omission] - for skipped words
   - [insertion] - for extra words added
   - [substitution] - for misread words
   - [repeats] - for repeated words
   - [self-correction] - for self-corrected errors
   - [hesitation] - for pauses or fillers
   - [question: "text"] - for student questions (include the question)
   - [agent_input] - for tutor interventions

3. Calculate KPIs:
   - Count of each miscue type
   - Words per minute (if timing info available, otherwise estimate)
   - Accuracy percentage (words read correctly / total words * 100)

**PASSAGE:**
{passage}

**TRANSCRIPT:**
{transcript}

**IMPORTANT INSTRUCTIONS:**
- Tags should be placed inline at the exact location where the event occurred
- Multiple tags can appear at one location if events coincided
- For questions, include the full question text in the tag
- Calculate accuracy as: (total words - omissions - substitutions - uncorrected errors) / total words * 100
- Words that were self-corrected should count as correct for accuracy
- Words requiring agent help count as errors
- Repetitions and hesitations don't reduce accuracy but should be counted

**OUTPUT FORMAT:**
Return ONLY a valid JSON object with this exact structure:
{{
  "cleaned_passage": "The passage text with [tags] inserted at appropriate locations",
  "kpis": {{
    "omissions": 0,
    "insertions": 0,
    "substitutions": 0,
    "repetitions": 0,
    "self_corrections": 0,
    "hesitations": 0,
    "questions": 0,
    "agent_interventions": 0,
    "words_per_minute": 30.0,
    "accuracy": 75.0,
    "total_words": 4,
    "words_read_correctly": 3
  }}
}}

Provide ONLY the JSON output, no additional explanation."""

        return prompt
    
    def analyze(self, passage: str, transcript: str) -> dict:
        """
        Analyze a reading session
        
        Args:
            passage: The text passage that should have been read
            transcript: The dialogue transcript between Reader and Tutor
            
        Returns:
            Dictionary with cleaned_passage and kpis
        """
        
        # Create initial state
        initial_state = ReadingState(
            passage=passage,
            transcript=transcript,
            cleaned_passage=None,
            kpis=None,
            analysis_result=None,
            error=None
        )
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        # Check for errors
        if final_state.get("error"):
            return {
                "error": final_state["error"],
                "cleaned_passage": "",
                "kpis": {}
            }
        
        # Return results
        return {
            "cleaned_passage": final_state.get("cleaned_passage", ""),
            "kpis": final_state.get("kpis", {})
        }
    
    def analyze_stream(self, passage: str, transcript: str):
        """
        Analyze a reading session with streaming output
        
        Args:
            passage: The text passage that should have been read
            transcript: The dialogue transcript between Reader and Tutor
            
        Yields:
            State updates as the workflow progresses
        """
        
        # Create initial state
        initial_state = ReadingState(
            passage=passage,
            transcript=transcript,
            cleaned_passage=None,
            kpis=None,
            analysis_result=None,
            error=None
        )
        
        # Stream the workflow execution
        for state in self.workflow.stream(initial_state):
            yield state


if __name__ == "__main__":
    # Example usage
    agent = ReadingAnalysisAgent()
    
    passage = "The cat is orange."
    transcript = """
Tutor: Please read this sentence.
Reader: The... The cat is ... how do I pronounce this word?
Tutor: "orange."
Reader: "orange."
"""
    
    print("Analyzing reading transcript...")
    result = agent.analyze(passage, transcript)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(json.dumps(result, indent=2))
