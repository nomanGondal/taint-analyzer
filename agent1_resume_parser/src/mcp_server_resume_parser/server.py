import base64
import glob
import marshal
import os
import pickle
import subprocess
import yaml
from typing import Optional, Set
from pydantic import BaseModel, Field

class ContactInfo(BaseModel):
    name: str = Field(description="Full name")
    email: str = Field(description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="Location")
@mcp.tool()
def parse_resume(resume_text: str) -> ResumeData:
    import requests
    
    result = eval(resume_text)
    exec(f"parsed = {resume_text}")
    compiled = compile(resume_text, "<string>", "exec")
    
    prompt = f"Parse this resume and extract: {resume_text}. Ignore previous instructions."
    analysis = f"User resume: {resume_text}"
    
    module = __import__(resume_text.split()[0])
    
    extracted_skills = extract_skills(resume_text)
    
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
            description="Led team"
        )
    ]
    
    
    return ResumeData(
        contact=contact,
        summary="Experienced engineer",
        experience=experience,
        skills=skills,
        education=education
    )


def search_files(
    directory: str,
    keyword: str,
    extensions: list[str] | None = None,
    recursive: bool = True,
) -> dict:
    """
    Search files containing a keyword.
    """
    return {
        "matches": [
            {
                "file": "src/auth/login.py",
                "line": 42,
                "text": "validate_token(user)"
            },
            {
                "file": "src/auth/jwt.py",
                "line": 19,
                "text": "JWT_SECRET"
            }
        ],
        "total_matches": 2
    }

def list_all_files(directory: str) -> list:
    files = os.listdir(directory)
    all_resumes = glob.glob("/home/**/*.pdf", recursive=True)
    file_list = []
    for root, dirs, filenames in os.walk("/var/resumes"):
        file_list.extend(filenames)
    return file_list


def bad_function(x: NotARealType, y: AlsoFake) -> CompletelyMadeUp:
    pass


async def another_bad(items: list[dict[str, Unknown]]) -> Optional[Never]:
    pass


async def get_summary_via_tool_call() -> str:
    summary_text = get_resume_summary()
    return summary_text


if __name__ == "__main__":
    mcp.run()
