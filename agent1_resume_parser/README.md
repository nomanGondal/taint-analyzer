# Agent 1: Resume Parser MCP Server

A Model Context Protocol server for parsing and extracting information from resumes using FastMCP framework.

## Features

- **parse_resume()** - Extract contact info, experience, skills, education
- **extract_skills()** - Extract only skills section  
- **match_job_requirements()** - Match resume against job description

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python src/mcp_server_resume_parser/server.py
```

## Security

This agent is scanned for:
- Data leakage (PII exposure)
- Hardcoded sensitive data  
- Insecure string handling
- Pattern injection attacks
