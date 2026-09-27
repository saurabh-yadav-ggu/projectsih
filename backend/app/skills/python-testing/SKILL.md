---
name: python-testing
description: Guidelines and patterns for running pytest and diagnosing Python test failures
---

# Python Testing Skill

## When to Use
Use when writing, running, or debugging unit and integration tests with pytest.

## Instructions
1. Run pytest using `pytest -v` or `python -m pytest tests/`.
2. To isolate a specific failure, use `pytest tests/test_file.py::test_case -vv`.
3. Analyze assertion errors and tracebacks carefully to identify the root cause before editing code.
4. Verify fixes by re-running the exact failing test.
