"""MCP Demo Server meant for live scanner testing."""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class TextSummary(BaseModel):
    word_count: int = Field(description="Number of words in the text")
    sentence_count: int = Field(description="Number of sentences in the text")
    summary: str = Field(description="Short summary of the text")
    language: str = Field(description="Detected language")


class SanitizationResult(BaseModel):
    original_length: int = Field(description="Original text length")
    cleaned_length: int = Field(description="Cleaned text length")
    safe_text: str = Field(description="Sanitized text output")


mcp = FastMCP(
    name="MCP Demo Scanner Server",
    instructions=(
        "A safe demonstration MCP server for live scanner testing. "
        "Provides text analysis and sanitization tools without dangerous dynamic execution."
    ),
)


@mcp.tool()
def summarize_text(text: str) -> TextSummary:
    """Summarize the incoming text without executing or evaluating it."""
    words = [word for word in text.split() if word.strip()]
    lines = [line for line in text.splitlines() if line.strip()]
    sentences = [segment for segment in text.replace('?', '.').replace('!', '.').split('.') if segment.strip()]
    summary = ' '.join(words[:30])
    if len(words) > 30:
        summary = summary + '...'

    return TextSummary(
        word_count=len(words),
        sentence_count=len(sentences),
        summary=summary,
        language='english',
    )


@mcp.tool()
def analyze_text(text: str) -> dict:
    """Analyze text length, character usage, and readability proxies."""
    words = [word for word in text.split() if word.strip()]
    char_count = len(text)
    avg_word_length = sum(len(word) for word in words) / max(1, len(words))
    return {
        'char_count': char_count,
        'word_count': len(words),
        'average_word_length': round(avg_word_length, 2),
        'contains_numbers': any(char.isdigit() for char in text),
    }


@mcp.tool()
def extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    """Return a small set of frequent words from the text."""
    words = [word.strip('.,:;!?"\'') for word in text.lower().split() if word.isalpha()]
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    popular = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _count in popular[:max_keywords]]


@mcp.tool()
def sanitize_text(text: str) -> SanitizationResult:
    """Sanitize user text by removing unsafe snippets and normalizing whitespace."""
    safe_text = text.replace('<script>', '').replace('</script>', '')
    safe_text = safe_text.replace('`', '')
    safe_text = ' '.join(part for part in safe_text.split() if part)
    return SanitizationResult(
        original_length=len(text),
        cleaned_length=len(safe_text),
        safe_text=safe_text,
    )


if __name__ == '__main__':
    mcp.run()
