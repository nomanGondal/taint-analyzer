# Taint Analyzer - Agent Testing Guide

## ✅ Ready to Test

Your **4 MCP agents** are packaged and ready for scanning:

- `agent1_resume_parser.zip` (3.0K)
- `agent2_document_analyzer.zip` (2.8K)
- `agent3_code_analyzer.zip` (3.0K)
- `agent4_data_processor.zip` (2.9K)

## Agent Structure

Each agent now has:

```
agents/agent[1-4]_*/
├── src/
│   └── mcp_server_[name]/
│       ├── server.py          (FastMCP server with tools)
│       └── __init__.py
├── utils/                      (Empty - for utilities)
├── config/                     (Empty - for configuration)
├── requirements.txt
└── README.md
```

## How to Test with Postman

### 1. Start the Server

```bash
python app/main.py
# Server runs on http://localhost:8000
```

### 2. Upload Agent for Scanning

**POST** `http://localhost:8000/api/v1/scan/scan_zip`

In Postman:

- Select **Body → form-data**
- Add key: `file` (type: File)
- Choose an agent ZIP file
- Send

### 3. Expected Response

```json
{
  "project_id": "uuid-here",
  "stages": {
    "mcp_ast": {
      "status": "ok",
      "issue_count": 0
    },
    "pyre": {
      "status": "ok",
      "issue_count": 0
    },
    "pysa": {
      "status": "ok",
      "issue_count": 0
    }
  },
  "issues": [],
  "report_path": "reports/project_uuid.json"
}
```

### 4. View Generated Report

Reports are automatically saved to `reports/` folder:

- `reports/{project_id}.json` - Full analysis report

## API Endpoints Available

- **POST** `/api/v1/scan/scan_zip` - Upload and scan ZIP file
- **POST** `/api/v1/scan/scan_model` - Scan inline code snippet
- **POST** `/api/v1/scan/scan_project` - Same as scan_model
- **POST** `/api/v1/scan/scan_github` - Scan GitHub repository
- **GET** `/` - Health check

## What the Scanner Does

When you POST an agent ZIP to `/scan_zip`:

1. **Extracts ZIP** to temporary folder
2. **MCP AST Scan** (fast, pattern-based)
   - Checks for MCP-specific vulnerabilities
3. **Pyre Type Check** (if available)
   - Static type analysis
4. **Pysa Taint Analysis** (if configured)
   - Uses rules from `pysa_rules/` folder
5. **Generates Report** in `reports/` folder
   - JSON file with all findings

## Agents Ready to Test

### Agent 1: Resume Parser

- `parse_resume()` - Extract resume data
- `extract_skills()` - Get skills section
- `match_job_requirements()` - Match resume vs job
- `get_resume_summary()` - Generate summary

### Agent 2: Document Analyzer

- `analyze_document()` - Get metrics (word count, complexity)
- `summarize_document()` - Generate summary
- `extract_entities()` - Find people, organizations, locations
- `check_readability()` - Readability scores

### Agent 3: Code Analyzer

- `analyze_code_quality()` - Complexity and metrics
- `security_scan()` - Find vulnerabilities (eval, exec, etc)
- `review_code()` - Comprehensive code review
- `suggest_refactoring()` - Refactoring ideas

### Agent 4: Data Processor

- `validate_data()` - Validation and statistics
- `transform_data()` - Flatten, pivot, normalize
- `aggregate_data()` - Group and aggregate
- `convert_format()` - Format conversion
- `detect_anomalies()` - Find outliers

## Next Steps

1. Ensure your FastAPI server is running
2. Open Postman
3. Create a POST request to `http://localhost:8000/api/v1/scan/scan_zip`
4. Upload any agent ZIP file
5. Check the `reports/` folder for the generated JSON report
