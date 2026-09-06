import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Annotated, Any, AsyncGenerator, Dict, List, Optional
from typing_extensions import TypedDict

# Configure UTF-8 encoding for standard output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import settings
from app.tools import local_tools
from app.mcp import get_mcp_tools, OUTPUT_DIR

logger = logging.getLogger("app.agent")

PROMPT_PATH = Path(__file__).resolve().parent / "prompt.json"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints.db"


def get_llm(temperature: float = 0.2) -> ChatOllama:
    """Initialize local Ollama LLM model."""
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=temperature,
    )


def get_base_system_prompt() -> str:
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("system_prompt", "You are ShieldAi assistant.")
    except Exception as e:
        logger.error(f"Failed to load prompt.json: {e}")
        return "You are a helpful AI assistant."


def _build_full_prompt(memory_context: str = "", document_context: str = "") -> str:
    base_prompt = get_base_system_prompt()
    prompt_parts = [base_prompt]

    if memory_context:
        prompt_parts.append(memory_context)

    if document_context:
        doc_prompt_block = (
            f"\n--- UPLOADED DOCUMENT CONTEXT FOR THIS THREAD ---\n"
            f"{document_context}\n"
            f"--- END UPLOADED DOCUMENT CONTEXT ---\n\n"
            f"CRITICAL INSTRUCTION: The document chunks above are active in this conversation thread. "
            f"When the user asks 'explain this document', 'summarize', or queries uploaded files, "
            f"directly review and summarize the provided document context above. Do NOT ask the user to provide the document again."
        )
        prompt_parts.append(doc_prompt_block)

    full_prompt = "\n\n".join(prompt_parts)
    full_prompt += (
        f"\n\nDocument Generation & Tool Guidelines:\n"
        f"- Output Directory: All generated documents are automatically saved under {OUTPUT_DIR.resolve().as_posix()}/<filename>.<ext>.\n"
        f"- To save any drafted text or report as a file (.docx, .xlsx, .pptx, .pdf, .html): First output the full content, then call 'save_as_document' with 'filename' (e.g. 'report.docx' or 'data.xlsx').\n"
        f"- To create Excel sheets directly: use 'create_excel_document' with 'output_path' (e.g. 'students.xlsx') and 'data' in CSV format ('Name,Score\\nJohn,85').\n"
        f"- To create Word documents: use 'create_word_document' with 'output_path' and 'markdown_content'.\n"
        f"- To create PowerPoint decks: use 'create_presentation_document' with 'output_path' and 'markdown_content' ('# Slide Title' and '---' for breaks).\n"
        f"- To create PDF documents: use 'create_pdf_document' with 'output_path' and 'markdown_content'.\n"
        f"- To create HTML pages: use 'create_html_document' with 'output_path' and 'markdown_content'.\n"
        f"- To read or convert existing files: use 'read_docx', 'read_pptx', 'read_xlsx', 'read_pdf', 'read_html', or 'convert_document'.\n"
        f"- After calling any document tool, ALWAYS report the final resulting file path on its own line exactly as:\n"
        f"FilePath: {OUTPUT_DIR.resolve().as_posix()}/<filename>.<ext>\n"
        f"so the user can preview and download it immediately.\n"
        f"- CRITICAL JSON FORMATTING: When generating tool arguments, all arguments MUST be valid single-line JSON strings without raw unescaped linebreaks. Use '\\n' (escaped) for linebreaks inside text/markdown strings.\n"
    )
    return full_prompt


# ---------------------------------------------------------------------------
# Deep Agent State & Nodes (Two-Stage Outliner & Executor Architecture)
# ---------------------------------------------------------------------------

class DeepAgentState(TypedDict):
    query: str
    thinking: str
    outline: str
    execution_log: List[str]
    final_response: str
    error: Optional[str]


async def outliner_subagent(state: DeepAgentState) -> Dict[str, Any]:
    """Node 1: Outliner & Thinking Sub-Agent using local Ollama model."""
    query = state["query"]
    print("\n" + "=" * 70)
    print("[SUB-AGENT 1: OUTLINER & ARCHITECT] Starting Deep Thinking & Planning (Local Ollama)...")
    print("=" * 70)

    prompt = f"""You are the Deep Outliner & Document Architect Sub-Agent.
Your mission is to perform deep thinking and create an honest, structured blueprint before any document is created.

CRITICAL RULES:
1. NEVER append or fabricate fake pre-baked datasets or hardcoded mock files.
2. Honestly evaluate feasibility: An LLM generates content within token limits. If a user asks for an unrealistic volume in a single chat turn (e.g. 1,000 distinct data rows with individual grades) without an external data file, clearly explain the technical limitation and propose a realistic sample size (e.g., 20-50 detailed records with full formulas) or explain how external data should be supplied.
3. If the request cannot be fulfilled as stated, explicitly state why in your thinking.

User Request: {query}

Please structure your response in this exact format:

### <THINKING>
- Intent & Feasibility: Can this be generated directly by an LLM within context window limits? What are the boundaries?
- Target Document Format(s): (.docx, .xlsx, .pptx, .pdf, or .html) and rationale.
- Data & Content Strategy: Exactly what data, structure, and formulas will be generated by the model.
- Error / Limitation Notice (if any): Any limitation the user must know.

### <DOCUMENT_OUTLINE_AND_PLAN>
- Target Filename(s): [e.g. report.docx, presentation.pptx, data.xlsx]
- Title: [Document Title]
- Detailed Structural Outline:
  * For Spreadsheets (.xlsx): Exact column schema, headers, sample rows to be generated, live formulas (=SUM, =AVERAGE).
  * For Presentation (.pptx): Slide breakdown (# Slide Title, bullet points, --- slide break).
  * For Documents (.docx / .pdf / .html): Full section breakdown and contents.
- Exact Instructions for the Execution Agent: Which MCP tool to invoke and what exact arguments to pass.
"""
    try:
        model = get_llm(temperature=0.2)
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = str(response.content)

        thinking = ""
        outline = content
        if "### <THINKING>" in content and "### <DOCUMENT_OUTLINE_AND_PLAN>" in content:
            parts = content.split("### <DOCUMENT_OUTLINE_AND_PLAN>")
            thinking = parts[0].replace("### <THINKING>", "").strip()
            outline = parts[1].strip()

        print("\n[THINKING PROCESS]:")
        print(thinking if thinking else "Feasibility and structure analyzed.")
        print("\n[GENERATED OUTLINE & BLUEPRINT]:")
        print(outline)
        print("=" * 70 + "\n")

        return {
            "thinking": thinking,
            "outline": outline,
            "execution_log": [f"Outline generated for: {query}"],
            "error": None,
        }
    except Exception as e:
        error_msg = f"Outliner Sub-Agent encountered an error: {str(e)}"
        print(f"[ERROR in Outliner]: {error_msg}")
        return {
            "thinking": "Failed during planning phase.",
            "outline": "",
            "execution_log": [error_msg],
            "error": error_msg,
            "final_response": f"Failed to plan document generation: {str(e)}",
        }


async def executor_subagent(state: DeepAgentState) -> Dict[str, Any]:
    """Node 2: Document Generation & Execution Sub-Agent using local Ollama model and MCP tools."""
    query = state["query"]
    outline = state["outline"]

    if state.get("error"):
        return {"final_response": f"Generation halted due to prior error: {state['error']}"}

    print("\n" + "=" * 70)
    print("[SUB-AGENT 2: DOCUMENT GENERATION & EXECUTION] Producing Documents (Local Ollama)...")
    print("=" * 70)

    execution_logs = list(state.get("execution_log", []))

    try:
        mcp_tools, _ = await get_mcp_tools()
        all_tools = list(local_tools) + list(mcp_tools)

        system_message = (
            "You are the Document Execution Sub-Agent running locally with Ollama. "
            "You have access to genuine MCP document tools: "
            "create_docx, create_pptx, create_xlsx, create_pdf, create_html, edit_xlsx, append_docx, etc. "
            "STRICT RULES: "
            "1. Do NOT fabricate or append fake pre-baked data files. "
            "2. Execute the approved outline using the MCP tools with real model-generated data. "
            "3. If any tool call fails or if the data cannot be generated, DO NOT hide the failure. "
            "Explicitly report the error and what failed to the user. "
            f"4. Output files are saved in {OUTPUT_DIR.resolve().as_posix()}/. "
            "After calling a document creation tool, always include:\n"
            f"FilePath: {OUTPUT_DIR.resolve().as_posix()}/<filename>.<ext>\n"
            "in your final response. "
            "5. All tool call arguments MUST be valid single-line JSON. NEVER output unescaped raw newlines inside string arguments."
        )

        model = get_llm(temperature=0.1)
        agent = create_agent(model, all_tools, system_prompt=system_message)

        executor_input = (
            f"Original User Request: {query}\n\n"
            f"Approved Document Outline & Plan:\n{outline}\n\n"
            "Execute this plan now using the genuine MCP document tools. "
            "If any tool fails or encounters errors, explain the error clearly to the user."
        )

        final_text = ""
        has_tool_error = False

        async for event in agent.astream({"messages": [("user", executor_input)]}, stream_mode="values"):
            last_message = event["messages"][-1]
            msg_type = last_message.type.upper()

            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                for call in last_message.tool_calls:
                    call_desc = f"[TOOL CALL] {call['name']}({call.get('args', {})})"
                    print(call_desc)
                    execution_logs.append(call_desc)

            if msg_type == "TOOL":
                result_snippet = str(last_message.content)
                if "error" in result_snippet.lower() or "exception" in result_snippet.lower():
                    has_tool_error = True
                    print(f"[TOOL ERROR]: {result_snippet}")
                else:
                    if len(result_snippet) > 200:
                        result_snippet = result_snippet[:200] + "..."
                    print(f"[TOOL RESULT]: {result_snippet}")
                execution_logs.append(f"[TOOL RESULT]: {result_snippet}")

            elif msg_type == "AI" and last_message.content:
                final_text = str(last_message.content)

        print("\n[SUB-AGENT 2 COMPLETED]:")
        print(final_text)
        print("=" * 70 + "\n")

        return {
            "execution_log": execution_logs,
            "final_response": final_text,
            "error": "Tool error detected during execution" if has_tool_error else None,
        }

    except Exception as e:
        error_msg = f"Execution Sub-Agent encountered an unexpected failure: {str(e)}"
        print(f"[ERROR in Executor]: {error_msg}")
        return {
            "execution_log": execution_logs + [error_msg],
            "final_response": f"Failed to generate documents. Reason: {str(e)}",
            "error": error_msg,
        }


def build_deep_agent():
    """Compile the two-stage Outliner -> Executor LangGraph."""
    workflow = StateGraph(DeepAgentState)
    workflow.add_node("outliner", outliner_subagent)
    workflow.add_node("executor", executor_subagent)

    workflow.add_edge(START, "outliner")
    workflow.add_edge("outliner", "executor")
    workflow.add_edge("executor", END)

    return workflow.compile()


deep_agent_app = build_deep_agent()


async def run_deep_agent(query: str):
    """Execute the two-stage Deep Agent with local Ollama model."""
    print(f"\n[DEEP AGENT RUNNER] Processing Query: '{query}'\n")
    initial_state = {
        "query": query,
        "thinking": "",
        "outline": "",
        "execution_log": [],
        "final_response": "",
        "error": None,
    }
    result = await deep_agent_app.ainvoke(initial_state)
    return result


# ---------------------------------------------------------------------------
# Project Web API Agent Execution (FastAPI Chat & Streaming Endpoints)
# ---------------------------------------------------------------------------

async def run_agent_query(
    message: str,
    thread_id: str,
    memory_context: str = "",
    document_context: str = "",
) -> str:
    """
    Executes the LangChain agent query using AsyncSqliteSaver checkpointer.
    Includes persistent user memories and thread document context in the prompt.
    Equipped with local tools (RAG, Vision, Calculator) and genuine MCP docgen tools.
    """
    mcp_tools, _ = await get_mcp_tools()
    all_tools = [*local_tools, *mcp_tools]

    full_prompt = _build_full_prompt(memory_context=memory_context, document_context=document_context)
    llm = get_llm(temperature=0)

    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH)) as checkpointer:
        agent = create_agent(
            model=llm,
            tools=all_tools,
            system_prompt=full_prompt,
            checkpointer=checkpointer,
        )

        inputs = {"messages": [HumanMessage(content=message)]}
        config = {"configurable": {"thread_id": thread_id}}

        result = await agent.ainvoke(inputs, config=config)

        messages = result.get("messages", [])
        if messages:
            return str(messages[-1].content)
        return "I processed your request, but generated no output text."


async def stream_agent_query(
    message: str,
    thread_id: str,
    memory_context: str = "",
    document_context: str = "",
) -> AsyncGenerator[str, None]:
    """
    Executes the LangChain agent query and streams LLM output tokens asynchronously.
    Equipped with local tools (RAG, Vision, Calculator) and genuine MCP docgen tools.
    """
    mcp_tools, _ = await get_mcp_tools()
    all_tools = [*local_tools, *mcp_tools]

    full_prompt = _build_full_prompt(memory_context=memory_context, document_context=document_context)
    llm = get_llm(temperature=0)

    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH)) as checkpointer:
        agent = create_agent(
            model=llm,
            tools=all_tools,
            system_prompt=full_prompt,
            checkpointer=checkpointer,
        )

        inputs = {"messages": [HumanMessage(content=message)]}
        config = {"configurable": {"thread_id": thread_id}}

        yielded_any = False
        try:
            async for event in agent.astream_events(inputs, config=config, version="v2"):
                kind = event.get("event")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if isinstance(content, str):
                            yielded_any = True
                            yield content
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, str):
                                    yielded_any = True
                                    yield part
                                elif isinstance(part, dict) and "text" in part:
                                    yielded_any = True
                                    yield part["text"]
        except Exception as e:
            logger.error(f"Streaming failed in stream_agent_query: {e}")
            if not yielded_any:
                logger.info("Attempting non-streaming fallback via run_agent_query...")
                try:
                    fallback_text = await run_agent_query(
                        message=message,
                        thread_id=thread_id,
                        memory_context=memory_context,
                        document_context=document_context,
                    )
                    yield fallback_text
                    return
                except Exception as fb_err:
                    logger.error(f"Fallback run_agent_query also failed: {fb_err}")
            raise e


# ---------------------------------------------------------------------------
# CLI Execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_query = "CREATE 5 PAGE REPORT ON THE history OF INDIAN AUTOMOBILE INDUSTRY WITH CHART AND GRAPHS"
    asyncio.run(run_deep_agent(test_query))