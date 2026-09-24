import pytest
from app.agent.router import route_query_intent
from app.agent.planner import generate_execution_plan


def test_route_query_intent_chat():
    assert route_query_intent("Hello, how are you?") == "chat"
    assert route_query_intent("Can you calculate 25 * 40?") == "chat"


def test_route_query_intent_document():
    assert route_query_intent("Create a 3-page quarterly report in Word") == "document"
    assert route_query_intent("Generate Excel spreadsheet for employee salaries") == "document"
    assert route_query_intent("Create presentation on AI architecture") == "document"


def test_route_query_intent_rag():
    assert route_query_intent("What is stated in the uploaded PDF file?") == "rag"
    assert route_query_intent("Summarize document chapter 2", has_document_context=True) == "rag"


def test_route_query_intent_vision():
    assert route_query_intent("Explain this chart", has_image=True) == "vision"


@pytest.mark.anyio
async def test_generate_execution_plan_chat():
    plan = await generate_execution_plan("Tell me a joke")
    assert plan["intent"] == "chat"
    assert len(plan["steps"]) > 0
