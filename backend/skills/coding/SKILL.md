---
name: coding
description: Instructions for generating Python code destined for execution in the isolated sandbox.
---

# Coding Skill

When writing Python code for the sandbox:

1. **Self-Contained Scripts**:
   - Write clean, standalone Python scripts.
   - Import only standard or allowed libraries (`os`, `sys`, `json`, `math`, `datetime`, `pathlib`, `docx`, `openpyxl`, `pptx`, `reportlab`, `pandas`, `csv`).
   - Do NOT use network libraries (`socket`, `requests`, `urllib`) unless explicitly authorized.
   - Do NOT call shell processes (`subprocess`, `os.system`).

2. **File Paths**:
   - Always read and write within the designated `target_path` or workspace directory.
   - Ensure parent directories exist (`Path(target_path).parent.mkdir(parents=True, exist_ok=True)`).

3. **Robust Error Handling**:
   - Print clear debug/progress messages to `stdout`.
   - On error, raise a descriptive exception so the diagnosis agent can analyze `stderr`.
