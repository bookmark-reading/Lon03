"""
Graph definition for LangGraph Studio
"""

from reading_agent import ReadingAnalysisAgent

# Export the agent for LangGraph Studio
__all__ = ["ReadingAnalysisAgent"]

# Create default instance
agent = ReadingAnalysisAgent()
graph = agent.workflow
