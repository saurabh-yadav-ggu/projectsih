---
name: verification
description: Quality criteria and inspection rules for generated artifacts across all supported document types.
---

# Verification Skill

All generated artifacts must undergo programmatic verification before being returned:

1. **Existence & Size**:
   - File must exist on disk and be non-empty (> 100 bytes).

2. **Format-Specific Verification**:
   - **DOCX**: File opens with `docx.Document`, contains > 0 paragraphs or tables, contains expected headings.
   - **XLSX**: File opens with `openpyxl.load_workbook`, contains expected sheets and > 1 row of data.
   - **PPTX**: File opens with `pptx.Presentation`, contains expected number of slides.
   - **PDF**: File opens with `pypdf.PdfReader` without errors, page count > 0.
   - **HTML**: File contains `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`, and non-empty content.

3. **Status Reporting**:
   - Output `PASS` with metadata or `FAIL` with descriptive error report for auto-remediation.
