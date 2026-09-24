from app.agent.router import route_query_intent
from app.services.skill_manager import skill_manager


def test_intent_routing_and_skill_matching():
    test_queries = [
        ("create a pdf from this text: financial summary", "document", "pdf"),
        ("generate pdf report", "document", "pdf"),
        ("make a spreadsheet of student scores", "document", "xlsx"),
        ("download presentation slides for quarterly review", "document", "pptx"),
        ("how can you create a pdf from this text: meeting notes", "document", "pdf"),
    ]
    for q, expected_intent, expected_format in test_queries:
        intent = route_query_intent(q)
        matched = skill_manager.match_skill(q)
        assert intent == expected_intent, f"Query '{q}' got intent '{intent}' instead of '{expected_intent}'"
        assert matched["format"] == expected_format, f"Query '{q}' got format '{matched['format']}' instead of '{expected_format}'"


def test_skill_crud_lifecycle():
    skill_name = "test_lifecycle_skill"
    # Create
    created = skill_manager.create_custom_skill(
        name=skill_name,
        title="Lifecycle Test Skill",
        description="Testing complete CRUD lifecycle of a custom user skill.",
        category="document",
        doc_format="pdf",
        content="# Test Content\n\nCustom instructions."
    )
    assert created["name"] == skill_name
    assert not created["is_system"]

    # Get
    fetched = skill_manager.get_skill(created["id"])
    assert fetched is not None
    assert fetched["title"] == "Lifecycle Test Skill"

    # Match by custom name
    matched = skill_manager.match_skill(f"Please use {skill_name} to generate report")
    assert matched["skill"]["name"] == skill_name

    # Update
    updated = skill_manager.update_custom_skill(created["id"], title="Updated Lifecycle Skill")
    assert updated["title"] == "Updated Lifecycle Skill"

    # Delete
    deleted = skill_manager.delete_custom_skill(created["id"])
    assert deleted is True

    # Verify deleted
    assert skill_manager.get_skill(created["id"]) is None


def test_installed_templates_present():
    installed_ids = [s["id"] for s in skill_manager.list_skills()]
    assert any("pdf-processing-pro" in sid for sid in installed_ids)
    assert any("docx-official" in sid for sid in installed_ids)
    assert any("pptx-official" in sid for sid in installed_ids)
    assert any("xlsx" in sid for sid in installed_ids)
    assert any("markitdown" in sid for sid in installed_ids)
    assert any("agent-management" in sid for sid in installed_ids)
    assert any("memory-search" in sid for sid in installed_ids)
    assert any("docs-search" in sid for sid in installed_ids)
    assert any("frontend-design" in sid for sid in installed_ids)
    assert any("documentation-templates" in sid for sid in installed_ids)


def test_vision_routing_and_analysis():
    from PIL import Image
    from pathlib import Path
    from app.vision import analyze_image

    # 1. Routing check
    assert route_query_intent("what is this?", has_image=True) == "vision"
    assert route_query_intent("analyze this screenshot") == "vision"

    # 2. Execution check
    test_img = Path("d:/sih/project/backend/uploads/test_unit_vision.png")
    test_img.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (200, 200), color=(100, 150, 200))
    img.save(test_img)

    try:
        report = analyze_image(str(test_img), "Inspect visual layout")
        assert isinstance(report, str) and len(report.strip()) > 5
    finally:
        if test_img.exists():
            test_img.unlink()


