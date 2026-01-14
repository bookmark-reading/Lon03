"""
Reading Transcript Analysis API
FastAPI server for analyzing reading transcripts
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
from reading_agent import ReadingAnalysisAgent

# Initialize FastAPI app
app = FastAPI(
    title="Reading Transcript Analysis API",
    description="Analyze reading transcripts to identify miscues and calculate KPIs using AWS Bedrock",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = ReadingAnalysisAgent()


class AnalysisRequest(BaseModel):
    """Request model for transcript analysis"""
    passage: str = Field(..., description="The target text that should be read")
    transcript: str = Field(..., description="What the student actually said (with STUDENT:/AGENT: labels)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "passage": "Mia packed her blue bag and ran to the park.\nIt was windy, so her kite tugged hard at the string.",
                "transcript": "STUDENT: Mia packed her... her blue bag and ran to park.\nSTUDENT: It was... um... window... no, windy, so her kite tug tugged hard at the the string."
            }
        }


class AnalysisResponse(BaseModel):
    """Response model for transcript analysis"""
    cleaned_passage: str = Field(..., description="Passage with inline miscue tags")
    kpis: dict = Field(..., description="Performance metrics and miscue counts")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Reading Transcript Analysis API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "analyze": "/analyze - POST - Analyze a reading transcript",
            "health": "/health - GET - Health check",
            "docs": "/docs - GET - Interactive API documentation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": agent.model_id,
        "region": agent.region
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_transcript(request: AnalysisRequest):
    """
    Analyze a reading transcript to identify miscues and calculate KPIs
    
    **Miscue Types Detected:**
    - Omissions: Skipped words
    - Insertions: Extra words added
    - Substitutions: Words misread
    - Repetitions: Words repeated
    - Self-corrections: Student self-corrected
    - Hesitations: Pauses or filler words
    - Questions: Student asked a question
    - Agent interventions: Tutor provided help
    
    **KPIs Calculated:**
    - Accuracy: Percentage of words read correctly
    - Words per minute (WPM)
    - Total error counts by type
    """
    try:
        result = agent.analyze(request.passage, request.transcript)
        return AnalysisResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
