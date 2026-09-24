import asyncio
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("app.sandbox.executor")

from app.sandbox.models import SandboxConfig, ExecutionResult
from app.sandbox.security import validate_code_safety


_RUNTIME_SHIMS = """# --- Shield Sandbox Runtime Compatibility Shims ---
try:
    import docx
    from docx.document import Document as _DocxDocument
    from docx.text.paragraph import Paragraph as _DocxParagraph
    from docx.table import _Cell as _DocxCell
    import docx.enum.text as _docx_enum_text

    # 1. Paragraph.font shim: redirect paragraph.font to its run font or style font
    if not hasattr(_DocxParagraph, "_shield_font_patched"):
        @property
        def _docx_p_font(self):
            if not self.runs:
                self.add_run()
            return self.runs[0].font
        _DocxParagraph.font = _docx_p_font
        _DocxParagraph._shield_font_patched = True

    # 2. Document.pages / page_count shim: return 1 rather than raising AttributeError
    if not hasattr(_DocxDocument, "_shield_pages_patched"):
        @property
        def _docx_doc_pages(self):
            return 1
        _DocxDocument.pages = _docx_doc_pages
        _DocxDocument.page_count = _docx_doc_pages
        _DocxDocument._shield_pages_patched = True

    # 3. Cell.add_run shim: allow cell.add_run() directly
    if not hasattr(_DocxCell, "_shield_cell_patched"):
        def _docx_cell_add_run(self, text=""):
            p = self.paragraphs[0] if self.paragraphs else self.add_paragraph()
            return p.add_run(text)
        _DocxCell.add_run = _docx_cell_add_run
        _DocxCell._shield_cell_patched = True

    # 4. Document.date shim: return current datetime when doc.date is accessed
    if not hasattr(_DocxDocument, "_shield_date_patched"):
        import datetime
        @property
        def _docx_doc_date(self):
            return datetime.datetime.now()
        _DocxDocument.date = _docx_doc_date
        _DocxDocument._shield_date_patched = True

    # 5. Table rows safe getitem shim: auto-add missing rows if index is out of bounds
    from docx.table import _Rows as _DocxRows
    if not hasattr(_DocxRows, "_shield_rows_patched"):
        _orig_rows_getitem = _DocxRows.__getitem__
        def _safe_rows_getitem(self, idx):
            if isinstance(idx, int) and idx >= len(self):
                while len(self) <= idx:
                    self.table.add_row()
            return _orig_rows_getitem(self, idx)
        _DocxRows.__getitem__ = _safe_rows_getitem
        _DocxRows._shield_rows_patched = True

    # 6. Enums shim: provide missing enum members commonly hallucinated
    if not hasattr(_docx_enum_text, "WD_HEADING"):
        _docx_enum_text.WD_HEADING = 1
    if not hasattr(_docx_enum_text, "WD_SECTION_START"):
        _docx_enum_text.WD_SECTION_START = 1
    if not hasattr(_docx_enum_text, "WD_ALIGN_VERTICAL"):
        _docx_enum_text.WD_ALIGN_VERTICAL = 1
except Exception:
    pass

try:
    from reportlab.lib.styles import StyleSheet1
    _orig_style_add = StyleSheet1.add
    def _safe_style_add(self, style, alias=None):
        if style.name in self.byName:
            self.byName[style.name] = style
            return
        return _orig_style_add(self, style, alias)
    StyleSheet1.add = _safe_style_add
except Exception:
    pass
# --- End Shield Sandbox Runtime Compatibility Shims ---
"""


class SandboxExecutor:
    """
    Subprocess-based isolated Python code executor.
    Enforces AST security, execution timeouts, clean environment variables,
    and captures stdout, stderr, and generated artifacts.
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()

    async def execute(
        self,
        code: str,
        workspace: Optional[Path] = None,
        timeout: Optional[int] = None,
        check_security: bool = True
    ) -> ExecutionResult:
        start_time = time.perf_counter()
        effective_timeout = timeout or self.config.timeout_seconds
        ws = Path(workspace) if workspace else (self.config.workspace_dir or Path(tempfile.gettempdir()))
        ws.mkdir(parents=True, exist_ok=True)

        # 1. AST Security Inspection
        if check_security:
            is_safe, violations = validate_code_safety(code, allowed_modules=self.config.allowed_modules)
            if not is_safe:
                return ExecutionResult(
                    success=False,
                    exit_code=1,
                    stdout="",
                    stderr=f"Security Violation: {'; '.join(violations)}",
                    artifacts=[],
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    error="Code failed sandbox security validation"
                )

        # Record pre-execution files in workspace
        pre_files = set(ws.glob("**/*")) if ws.exists() else set()

        # 2. Write code to an isolated system temporary script file
        # CRITICAL: Written outside the project tree to prevent Uvicorn's file watcher from reloading
        temp_scripts_dir = Path(tempfile.gettempdir()) / "shield_sandbox_scripts"
        temp_scripts_dir.mkdir(parents=True, exist_ok=True)
        script_file = temp_scripts_dir / f"_script_{int(time.time() * 1000)}.py"
        try:
            executable_code = f"{_RUNTIME_SHIMS}\n\n{code}"
            script_file.write_text(executable_code, encoding="utf-8")

            # 3. Prepare sanitized environment
            safe_env = {
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
                "PYTHONPATH": os.path.abspath(str(Path(__file__).resolve().parent.parent.parent)),
            }
            # Suppress network proxy variables
            if self.config.block_network:
                safe_env["HTTP_PROXY"] = ""
                safe_env["HTTPS_PROXY"] = ""
                safe_env["ALL_PROXY"] = ""

            # 4. Launch subprocess (with fallback for Windows event loops lacking asyncio subprocess support)
            stdout = ""
            stderr = ""
            exit_code = 0
            success = False
            error_msg = None

            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(script_file),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(ws),
                    env=safe_env
                )
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=effective_timeout
                    )
                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                    exit_code = process.returncode or 0
                    success = (exit_code == 0)
                    error_msg = None if success else f"Process exited with code {exit_code}"
                except asyncio.TimeoutError:
                    try:
                        process.kill()
                        await process.wait()
                    except Exception:
                        pass
                    return ExecutionResult(
                        success=False,
                        exit_code=124,
                        stdout="",
                        stderr=f"Execution timed out after {effective_timeout} seconds.",
                        artifacts=[],
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                        error="Execution timeout"
                    )
            except (NotImplementedError, AttributeError):
                # Windows SelectorEventLoop or environments lacking asyncio subprocess support
                logger.info("Using subprocess.run via asyncio.to_thread fallback for sandbox execution.")
                def _run_sync():
                    return subprocess.run(
                        [sys.executable, str(script_file)],
                        capture_output=True,
                        cwd=str(ws),
                        env=safe_env,
                        timeout=effective_timeout
                    )
                try:
                    cp = await asyncio.to_thread(_run_sync)
                    stdout = cp.stdout.decode("utf-8", errors="replace") if isinstance(cp.stdout, bytes) else str(cp.stdout)
                    stderr = cp.stderr.decode("utf-8", errors="replace") if isinstance(cp.stderr, bytes) else str(cp.stderr)
                    exit_code = cp.returncode or 0
                    success = (exit_code == 0)
                    error_msg = None if success else f"Process exited with code {exit_code}"
                except subprocess.TimeoutExpired:
                    return ExecutionResult(
                        success=False,
                        exit_code=124,
                        stdout="",
                        stderr=f"Execution timed out after {effective_timeout} seconds.",
                        artifacts=[],
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                        error="Execution timeout"
                    )

            # 5. Detect generated artifacts
            post_files = set(ws.glob("**/*")) if ws.exists() else set()
            new_files = [
                str(f.resolve()) for f in (post_files - pre_files)
                if f.is_file() and f != script_file
            ]

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(
                success=success,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                artifacts=new_files,
                execution_time_ms=elapsed_ms,
                error=error_msg
            )

        finally:
            # Clean up temporary script
            if script_file.exists():
                try:
                    script_file.unlink()
                except Exception:
                    pass
