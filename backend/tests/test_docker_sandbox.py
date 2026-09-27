"""
Integration and Security Test Suite for Real Local Docker Sandbox in Deep Agents.

Verifies:
1. Python execution inside isolated container: `python3 -c "print(2 + 2)"`
2. File creation: `/workspace/test.txt` persists to host workspace mount
3. File persistence across commands: File created in step 2 can be read by subsequent command
4. Failure reporting: `python3 -c "raise Exception('test')"` returns non-zero code and captures error
5. Timeout termination: Long process terminates when timeout is reached
6. Isolation: Host filesystem is not mounted, docker socket is absent
7. Network disabled: Container cannot make outbound network requests
8. Document generation: Real DOCX/PDF/XLSX generation inside sandbox with output in workspace
"""

import pytest
import subprocess
from pathlib import Path

from app.sandbox.docker_backend import DockerSandboxBackend
from app.sandbox.docker_executor import DockerSandboxExecutor
from app.sandbox.health import check_sandbox_health


@pytest.fixture
def sandbox(tmp_path: Path):
    """Provides a real DockerSandboxBackend instance bound to a temporary workspace."""
    sb = DockerSandboxBackend(
        workspace_dir=tmp_path,
        session_id=f"test-{tmp_path.name}",
        allow_network=False,
        timeout=15,
    )
    yield sb
    sb.close()


def test_health_check():
    """Verify health check utility detects Docker and image."""
    health = check_sandbox_health()
    assert health["status"] == "healthy"
    assert health["checks"]["docker_available"] is True
    assert health["checks"]["image_available"] is True
    assert health["checks"]["container_startable"] is True
    assert health["checks"]["workspace_writable"] is True
    assert health["checks"]["command_execution"] is True


def test_1_python_execution(sandbox: DockerSandboxBackend):
    """Test 1: Agent executes `python3 -c 'print(2 + 2)'` -> expected '4'."""
    res = sandbox.execute("python3 -c 'print(2 + 2)'")
    assert res.exit_code == 0
    assert "4" in res.output.strip()


def test_2_file_creation(sandbox: DockerSandboxBackend, tmp_path: Path):
    """Test 2: Create `/workspace/test.txt` and verify it exists on host."""
    res = sandbox.execute("echo 'hello sandbox' > /workspace/test.txt")
    assert res.exit_code == 0

    host_file = tmp_path / "test.txt"
    assert host_file.exists()
    assert host_file.read_text().strip() == "hello sandbox"


def test_3_persistence_across_commands(sandbox: DockerSandboxBackend):
    """Test 3: Create a file, execute another command, and verify reading."""
    res1 = sandbox.execute("echo 'persistent data 12345' > /workspace/data.log")
    assert res1.exit_code == 0

    res2 = sandbox.execute("cat /workspace/data.log")
    assert res2.exit_code == 0
    assert "persistent data 12345" in res2.output


def test_4_failure_reporting(sandbox: DockerSandboxBackend):
    """Test 4: Failing command returns non-zero exit code and error details."""
    res = sandbox.execute("python3 -c \"raise Exception('deliberate_failure')\"")
    assert res.exit_code != 0
    assert "Exception: deliberate_failure" in res.output


def test_5_timeout_enforcement(sandbox: DockerSandboxBackend):
    """Test 5: Process exceeding timeout is killed with exit code 124."""
    res = sandbox.execute("sleep 10", timeout=2)
    assert res.exit_code == 124
    assert "timed out after 2 seconds" in res.output.lower()


def test_6_isolation(sandbox: DockerSandboxBackend):
    """Test 6: Verify container cannot access arbitrary host files or Docker socket."""
    # Docker socket must NOT exist in sandbox
    res_sock = sandbox.execute("test -S /var/run/docker.sock && echo 'EXISTS' || echo 'SECURE'")
    assert "SECURE" in res_sock.output

    # No host root mount
    res_host = sandbox.execute("test -d /host && echo 'HOST_EXPOSED' || echo 'ISOLATED'")
    assert "ISOLATED" in res_host.output


def test_7_network_isolation(sandbox: DockerSandboxBackend):
    """Test 7: When network is disabled, external network connections fail."""
    res = sandbox.execute("curl -m 2 http://example.com 2>&1")
    # curl should fail with couldn't connect or timeout
    assert res.exit_code != 0


def test_8_document_generation(sandbox: DockerSandboxBackend, tmp_path: Path):
    """Test 8: Generate real DOCX, XLSX, and PDF in /workspace and verify files exist."""
    doc_script = """
import docx
doc = docx.Document()
doc.add_heading('Deep Agents Sandbox Report', 0)
doc.add_paragraph('Verified isolated document generation.')
doc.save('/workspace/sample.docx')

import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws['A1'] = 'Metric'
ws['B1'] = 'Value'
ws['A2'] = 'CPU Limit'
ws['B2'] = 2.0
wb.save('/workspace/metrics.xlsx')

from reportlab.pdfgen import canvas
c = canvas.Canvas('/workspace/report.pdf')
c.drawString(100, 750, 'Deep Agents PDF Artifact')
c.save()
"""
    res = sandbox.execute(f"python3 -c \"{doc_script}\"")
    assert res.exit_code == 0

    # Verify all generated artifacts exist on the host workspace
    docx_file = tmp_path / "sample.docx"
    xlsx_file = tmp_path / "metrics.xlsx"
    pdf_file = tmp_path / "report.pdf"

    assert docx_file.exists() and docx_file.stat().st_size > 0
    assert xlsx_file.exists() and xlsx_file.stat().st_size > 0
    assert pdf_file.exists() and pdf_file.stat().st_size > 0


def test_9_node_execution(sandbox: DockerSandboxBackend):
    """Test 9: Verify Node.js and npm are available and can execute scripts."""
    res = sandbox.execute("node -e \"console.log(JSON.stringify({status: 'ok', product: 6 * 7}))\"")
    assert res.exit_code == 0
    assert '"product":42' in res.output or '"product": 42' in res.output


def test_10_git_operations(sandbox: DockerSandboxBackend):
    """Test 10: Verify Git repository operations work inside the workspace."""
    git_cmds = """
cd /workspace
git config --global --add safe.directory '*'
git init -b main
git config user.email "sandbox@shield.ai"
git config user.name "Sandbox User"
echo "console.log('shield');" > app.js
git add app.js
git commit -m "initial commit"
git log -n 1 --oneline
"""
    res = sandbox.execute(git_cmds)
    assert res.exit_code == 0
    assert "initial commit" in res.output


def test_11_pandoc_and_libreoffice_tools(sandbox: DockerSandboxBackend):
    """Test 11: Verify Pandoc and LibreOffice headless utilities are present."""
    res_pandoc = sandbox.execute("pandoc --version")
    assert res_pandoc.exit_code == 0
    assert "pandoc" in res_pandoc.output.lower()

    res_soffice = sandbox.execute("soffice --version || libreoffice --version")
    assert res_soffice.exit_code == 0
    assert "libreoffice" in res_soffice.output.lower()


def test_12_upload_and_download_files(sandbox: DockerSandboxBackend):
    """Test 12: Verify upload_files and download_files conform to Deep Agents protocol."""
    upload_res = sandbox.upload_files([
        ("hello.txt", b"file content 1"),
        ("nested/doc.txt", "string text 2"),
    ])
    assert len(upload_res) == 2
    assert upload_res[0].path == "hello.txt"
    assert upload_res[0].error is None
    assert upload_res[1].path == "nested/doc.txt"
    assert upload_res[1].error is None

    download_res = sandbox.download_files(["hello.txt", "nested/doc.txt", "nonexistent.txt"])
    assert len(download_res) == 3
    assert download_res[0].path == "hello.txt"
    assert download_res[0].content == b"file content 1"
    assert download_res[0].error is None

    assert download_res[1].path == "nested/doc.txt"
    assert download_res[1].content == b"string text 2"
    assert download_res[1].error is None

    assert download_res[2].path == "nonexistent.txt"
    assert download_res[2].content is None
    assert download_res[2].error == "file_not_found"


@pytest.mark.anyio
async def test_docker_sandbox_executor(tmp_path: Path):
    """Verify DockerSandboxExecutor end-to-end async Python execution."""
    executor = DockerSandboxExecutor()
    code = "import math; print('SQRT:', math.isqrt(144))"
    res = await executor.execute(code=code, workspace=tmp_path)
    assert res.success is True
    assert res.exit_code == 0
    assert "SQRT: 12" in res.stdout

