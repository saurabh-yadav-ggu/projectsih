# MCP & Document Generation Implementation Guide

## Executive Summary

This document provides a comprehensive technical overview of the implementation, architecture, and resolution of the Ollama HTTP 500 error:
```
Error: invalid character '\n' in string literal (status code: 500)
```
which occurred when the local agent (`ministral-3:3b` via Ollama) drafted and generated documents such as Word documents (`.docx`), Excel spreadsheets (`.xlsx`), PowerPoint presentations (`.pptx`), PDFs, and HTML files.

---

## 1. Problem Statement & Root Cause Analysis

### 1.1 The Symptom
During document creation requests (e.g., *"draft an offer letter in docs"* or *"generate an excel file of 10 student records with names and marks"*), the chat stream unexpectedly terminated with:
- `Error: invalid character '\n' in string literal (status code: 500)`
- `invalid character ']' after object key:value pair (status code: 500)`

### 1.2 The Root Cause
1. **Ollama Go Template Injection**:
   - Ollama passes tool schemas to the model by embedding function descriptions into Go text templates:
     `"description": "{{ .Function.Description }}"`
   - When tools from `mcp-docgen` or local Python functions had multi-line docstrings containing raw newline characters (`0x0A`), Ollama's Go template renderer produced invalid JSON containing unescaped raw newlines inside string literals.

2. **Model BPE Tokenization & Tool-Calling Syntax**:
   - Small quantized local models (such as `ministral-3:3b`) naturally output literal line breaks (`0x0A`) rather than escaped `\n` characters when generating multi-line text (like Markdown content) or complex nested JSON structures (`sheets: [{"name": "...", "rows": [["...", ...]]}]`).
   - Ollama parses model-generated tool calls with Go's `encoding/json` (`json.Unmarshal`). Any literal newline byte or misplaced syntax token inside a JSON string immediately crashes Ollama's Go server with HTTP status code 500.

---

## 2. Architectural Solution

To achieve 100% reliability with local Ollama models, a multi-layer resilient architecture was implemented:

```
┌────────────────────────────────────────────────────────┐
│                   Frontend (React/Vite)                │
│             SSE Streaming & Download Handler           │
└───────────────────────────▲────────────────────────────┘
                            │ /api/chat/stream
┌───────────────────────────┴────────────────────────────┐
│               FastAPI & LangGraph ReAct Agent          │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Prompt Constraints (Valid Single-Line JSON)     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Resilient Tools Layer                            │  │
│  │  ├─ save_as_document (InjectedState content)     │  │
│  │  ├─ create_excel_document (CSV text parser)      │  │
│  │  ├─ create_word_document (Direct docx_writer)    │  │
│  │  ├─ create_presentation_document (pptx_writer)   │  │
│  │  └─ create_pdf_document / create_html_document   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ MCP Tool Sanitizer (Strips \r and \n from desc)  │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│                    Ollama (ministral-3:3b)             │
│            Local LLM Inference (Zero Cloud Cost)       │
└────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Details

### 3.1 Tool Metadata Sanitization (`backend/app/mcp/mcp_client.py`)
All tool descriptions loaded from the `mcp-docgen` server are sanitized upon startup to eliminate raw newlines and condense extraneous whitespace:

```python
# Strip newlines from tool descriptions to prevent Ollama Go template errors
for tool in mcp_tools:
    if tool.description:
        tool.description = " ".join(tool.description.split())
```

**Result**: All 17 MCP tools now have strictly single-line descriptions, preventing Go template injection errors in Ollama.

---

### 3.2 High-Level Resilient Document Tools (`backend/app/tools.py`)

Rather than forcing the 3B model to generate thousands of tokens of multi-line Markdown or nested JSON arrays inside tool arguments, high-level helper tools were implemented:

#### A. `save_as_document` (with LangGraph `InjectedState`)
This tool allows the agent to first draft the document naturally in the chat conversation, and then save it using only the target filename:

```python
@tool
def save_as_document(
    filename: str,
    state: Annotated[dict, InjectedState],
    content: str = "",
    title: str = ""
) -> str:
    """Save previously drafted content or markdown text as a document (.docx, .xlsx, .pptx, .pdf, or .html). Only filename is required."""
    # If the model does not provide content, automatically extract the latest draft from the conversation state:
    if not content:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and len(msg.content) > 50:
                content = msg.content
                break
    # Routes to docx_writer, openpyxl, pptx_writer, pdf_writer, or html_writer
```

**Benefit**: Eliminates the need for the model to serialize large markdown bodies into JSON tool arguments.

#### B. `create_excel_document` (CSV Text Parser)
Replaces complex nested sheet arrays with simple comma-separated or tab-separated text:

```python
@tool
def create_excel_document(output_path: str, data: str, sheet_name: str = "Sheet1") -> str:
    """Create an Excel (.xlsx) file from CSV-formatted text data (e.g. 'Name,Marks\\nJohn,85')."""
    # Uses Python's built-in csv.reader and openpyxl
    # Safe against Go JSON syntax errors
```

#### C. Dedicated Document Converters
- `create_word_document(output_path: str, markdown_content: str, title: str = "")`: Direct conversion to styled Word `.docx`.
- `create_presentation_document(output_path: str, markdown_content: str, title: str = "")`: Direct conversion to PowerPoint `.pptx` (slides separated by `---`).
- `create_pdf_document(output_path: str, markdown_content: str, title: str = "")`: Direct conversion to PDF.
- `create_html_document(output_path: str, markdown_content: str, title: str = "")`: Direct conversion to standalone styled HTML.

---

### 3.3 Prompt Engineering & Argument Rules (`backend/app/agent.py` & `backend/app/prompt.json`)

The system prompt explicitly instructs the model on strict JSON argument formatting:

```text
DOCUMENT CREATION RULES:
1. When asked to draft or create a document (Word, Excel, PowerPoint, PDF, HTML):
   - First, write out the complete draft content in your response message.
   - Then call 'save_as_document' with just the filename (e.g., 'offer_letter.docx').
2. For spreadsheets and tabular data, you can also use 'create_excel_document' by providing simple CSV data.
3. CRITICAL JSON FORMATTING: When generating tool arguments, all arguments MUST be valid single-line JSON strings without raw unescaped linebreaks. Use '\n' (escaped) for linebreaks inside text/markdown strings.
4. After creating any document, always state the exact output path so the user can download it. Format: FilePath: <path>
```

---

### 3.4 Resilient Streaming Pipeline (`backend/app/agent.py`)

In `stream_agent_query`, `agent.astream_events` is wrapped in exception handling with an automatic fallback to `run_agent_query`:

```python
try:
    async for event in agent.astream_events(inputs, config, version="v2"):
        # Yield token events and tool execution indicators
        ...
except Exception as stream_err:
    logger.warning(f"astream_events encountered error: {stream_err}. Falling back to run_agent_query...")
    result = await run_agent_query(query, thread_id=thread_id)
    # Yield result to client without crashing SSE
```

---

## 4. Key Files Reference

| File | Path | Role |
| :--- | :--- | :--- |
| **Tool Client** | `backend/app/mcp/mcp_client.py` | Initializes `mcp-docgen` and sanitizes tool descriptions to single-line strings. |
| **Document Tools** | `backend/app/tools.py` | Provides `save_as_document`, `create_excel_document`, `create_word_document`, etc. |
| **ReAct Agent** | `backend/app/agent.py` | Configures LangGraph ReAct agent, state management, and resilient SSE streaming. |
| **Prompts** | `backend/app/prompt.json` | Master system prompt containing tool-calling rules and JSON syntax constraints. |
| **Document Router** | `backend/app/routers/documents.py` | Serves generated documents from `backend/app/mcp/out/` for download. |
| **Output Directory** | `backend/app/mcp/out/` | Destination folder for all generated `.docx`, `.xlsx`, `.pptx`, `.pdf`, `.html` files. |

---

## 5. Verification & Test Results

### 5.1 Tool Metadata Verification
- **Test**: Iterated through all 20 active agent tools (`local_tools` + `mcp_tools`).
- **Result**: `SUCCESS: All tool descriptions are strictly single-line without raw newlines.`

### 5.2 Word Document Generation Test
- **Prompt**: `"can you draft a offer leter for software delevpment role in docs"`
- **Execution Flow**:
  1. The agent drafted a comprehensive offer letter directly into the chat stream.
  2. The agent called `save_as_document(filename="software_developer_offer_letter.docx")`.
  3. `save_as_document` retrieved the drafted content from `InjectedState` and compiled it into a `.docx` document.
  4. File created: `backend/app/mcp/out/software_developer_offer_letter.docx` (38,183 bytes, 37 paragraphs).
  5. Chat rendered download card with: `FilePath: D:/sih/project/backend/app/mcp/out/software_developer_offer_letter.docx`.
- **Status**: **PASSED (0 errors)**.

### 5.3 Excel Spreadsheet Generation Test
- **Prompt**: `"generate excel file of 10 student records with names and marks"`
- **Execution Flow**:
  1. The agent called `create_excel_document` passing standard CSV-formatted lines.
  2. Built-in `csv.reader` parsed data into rows and `openpyxl` rendered the worksheet.
  3. File created: `backend/app/mcp/out/student_records.xlsx` (5,261 bytes, 11 rows).
  4. Chat rendered download card with: `FilePath: D:/sih/project/backend/app/mcp/out/student_records.xlsx`.
- **Status**: **PASSED (0 errors)**.

---

## 6. How to Use & Extend

### 6.1 Creating a Word / Presentation / PDF Document
To request any document, prompt the assistant in natural language:
- *"Draft an employee non-disclosure agreement and save it as a Word document."*
- *"Create a 5-slide presentation on Artificial Intelligence trends."*
- *"Generate a PDF report on Q3 financial performance."*

The assistant will draft the content, invoke `save_as_document`, and provide a direct download link.

### 6.2 Creating an Excel Spreadsheet
To generate an Excel workbook:
- *"Create an Excel sheet with 15 product inventory items including ID, Name, Price, and Stock."*

The assistant invokes `create_excel_document` and provides the downloadable `.xlsx` file.

### 6.3 Adding New Document Types or Tools
When adding new tools to `backend/app/tools.py`:
1. Keep the docstring strictly on **one line** without literal line breaks.
2. Avoid deeply nested array parameters; prefer flat primitives or simple delimited strings (e.g. CSV).
3. For file outputs, always place the final file in `OUTPUT_DIR` and prefix the return string with `FilePath: <absolute_path>`.
