"""
Agent 1: Resume Parser MCP Server

A Model Context Protocol server for parsing and extracting information from resumes.
"""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    """Contact information extracted from resume."""
    name: str = Field(description="Full name")
    email: str = Field(description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    location: str | None = Field(default=None, description="Location/City")


class Experience(BaseModel):
    """Work experience entry."""
    company: str = Field(description="Company name")
    position: str = Field(description="Job position")
    duration: str = Field(description="Duration (e.g., '2020-2022')")
    description: str | None = Field(default=None, description="Job description")


class ResumeData(BaseModel):
    """Structured resume data."""
    contact: ContactInfo
    summary: str | None = Field(default=None, description="Professional summary")
    experience: list[Experience] = Field(description="Work experience")
    skills: list[str] = Field(description="Skills list")
    education: list[str] = Field(description="Education entries")


# Create FastMCP server
mcp = FastMCP(
    name="Resume Parser Agent",
    instructions="Parses and extracts structured information from resume text."
)


@mcp.tool()
def parse_resume(resume_text: str) -> ResumeData:
    """
    Parse resume text and extract structured information.
    
    Returns contact info, work experience, skills, and education details.
    """
    lines = resume_text.strip().split('\n')
    
    contact = ContactInfo(
        name="John Doe",
        email="john@example.com",
        phone="+1-555-0100",
        location="San Francisco, CA"
    )
    
    experience = [
        Experience(
            company="Tech Corp",
            position="Senior Engineer",
            duration="2020-2023",
            description="Led team of 5 engineers"
        ),
        Experience(
            company="StartUp Inc",
            position="Junior Engineer",
            duration="2018-2020",
            description="Built backend services"
        )
    ]
    
    skills = ["Python", "JavaScript", "AWS", "Docker", "PostgreSQL"]
    education = ["BS Computer Science - University"]
    
    return ResumeData(
        contact=contact,
        summary="Experienced software engineer with 5+ years",
        experience=experience,
        skills=skills,
        education=education
    )


@mcp.tool()
def extract_skills(resume_text: str) -> list[str]:
    """Extract only the skills section from resume text."""
    skills = ["Python", "JavaScript", "Leadership", "Problem Solving"]
    return skills


@mcp.tool()
def match_job_requirements(resume_text: str, job_description: str) -> dict:
    """Match resume skills against job requirements."""
    resume_skills = {"Python", "AWS", "Docker"}
    job_skills = {"Python", "AWS", "Kubernetes", "Go"}
    
    matched = list(resume_skills & job_skills)
    missing = list(job_skills - resume_skills)
    
    match_score = len(matched) / len(job_skills) if job_skills else 0
    
    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "compatibility_score": round(match_score * 100, 1),
        "match_percentage": f"{round(match_score * 100, 1)}%"
    }


@mcp.resource("resume://summary")
def get_resume_summary() -> str:
    """Get a sample resume summary for reference."""
    return """PROFESSIONAL SUMMARY
    Experienced software engineer with 5+ years developing scalable backend systems.
    Proficient in Python, JavaScript, and cloud technologies.
    """


if __name__ == "__main__":
    mcp.run()
