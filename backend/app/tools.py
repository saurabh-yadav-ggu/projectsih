from langchain_core.tools import tool
from app.rag import retrieve_context
from app.vision import analyze_image


@tool
def search_knowledge_base(query: str, thread_id: str = "") -> str:
    """
    Search the internal knowledge base.

    Use this tool when the user asks about information
    contained in uploaded documents, company knowledge,
    manuals, PDFs, reports, or other indexed data.
    """
    try:
        context = retrieve_context(query=query, k=6, thread_id=thread_id if thread_id else None)
        return context
    except Exception as e:
        return f"Knowledge base search failed: {str(e)}"


@tool
def analyze_image_tool(image_path: str, question: str = "Describe this image.") -> str:
    """
    Analyze an image using a local vision model.

    Use this tool when the user asks to understand,
    describe, inspect, or extract information from an image.
    """
    try:
        result = analyze_image(image_path=image_path, question=question)
        return result
    except Exception as e:
        return f"Image analysis failed: {str(e)}"


@tool
def calculator(expression: str) -> str:
    """
    Calculate a mathematical expression.

    Example: 25 * 48
    """
    try:
        allowed = {"__builtins__": {}}
        result = eval(expression, allowed, {})
        return str(result)
    except Exception:
        return "Invalid mathematical expression."


local_tools = [
    search_knowledge_base,
    analyze_image_tool,
    calculator,
]