"""Agent 2: Document Analyzer MCP Server."""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class DocumentAnalysis(BaseModel):
    """Analysis results for a document."""
    word_count: int = Field(description="Total word count")
    sentence_count: int = Field(description="Number of sentences")
    paragraph_count: int = Field(description="Number of paragraphs")
    reading_level: str = Field(description="Estimated reading level")
    key_terms: list[str] = Field(description="Important terms in document")


# mcp = FastMCP(
#     name="Document Analyzer Agent",
#     instructions="Analyzes document content, extracts insights, and provides summaries."
# )

@mcp.tool()
def extract_entities(document_text: str) -> dict:
    """Extract named entities from document."""
    return {
        "people": ["John Smith", "Jane Doe"],
        "organizations": ["Acme Corp", "Tech Industries"],
        "locations": ["New York", "San Francisco"],
        "dates": ["2024-01-15", "2024-12-31"]
    }


@mcp.tool()
def check_readability(document_text: str) -> dict:
    """Check document readability metrics."""
    return {
        "flesch_kincaid_grade": 8.5,
        "readability_score": 65,
        "grade_level": "8th Grade",
        "suggestions": ["Use shorter sentences", "Replace complex words", "Break content into shorter paragraphs"]
    }


if __name__ == "__main__":
    mcp.run()
