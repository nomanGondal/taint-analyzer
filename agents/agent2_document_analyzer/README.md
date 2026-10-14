# Agent 2: Document Analyzer MCP Server

A Model Context Protocol server for analyzing document content.

## Features

- **analyze_document()** - Get metrics: word count, readability, key terms
- **summarize_document()** - Generate concise summary
- **extract_entities()** - Extract people, organizations, locations
- **check_readability()** - Get readability scores and suggestions

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python src/mcp_server_document_analyzer/server.py
```
