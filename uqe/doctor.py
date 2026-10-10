"""
UQE Doctor — Environment, Toolchain, and Project Diagnostics
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

PRIME_DIRECTIVE = (
    "Assume nothing. Verify everything. Use the cheapest sufficient evidence. "
    "Do not ship blind. Do not fabricate. Do not over-process trivial work."
)

class DiagnosticResult:
    def __init__(self, name: str, status: str, message: str, is_warning: bool = False):
        self.name = name
        self.status = status  # OK, WARN, FAIL, INFO
        self.message = message
        self.is_warning = is_warning

def check_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def get_command_version(cmd: str, args: list) -> str:
    try:
        res = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=5)
        out = (res.stdout or res.stderr).strip().splitlines()
        return out[0] if out else "installed"
    except Exception:
        return "installed"

def diagnose(workspace: Path = None) -> int:
    if workspace is None:
        workspace = Path.cwd()

    results = []

    # 1. Python Environment
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 9):
        results.append(DiagnosticResult("Python Runtime", "OK", f"Python {py_ver} ({sys.executable})"))
    else:
        results.append(DiagnosticResult("Python Runtime", "FAIL", f"Python {py_ver} (Require >= 3.9)"))

    # 2. Operating System
    results.append(DiagnosticResult("Operating System", "INFO", f"{platform.system()} {platform.release()} ({platform.machine()})"))

    # 3. Core Tools
    if check_command("git"):
        git_ver = get_command_version("git", ["--version"])
        results.append(DiagnosticResult("Git VCS", "OK", git_ver))
    else:
        results.append(DiagnosticResult("Git VCS", "WARN", "git not found in PATH", is_warning=True))

    # 4. Integrity Tools
    has_sha = check_command("sha256sum") or check_command("shasum") or (platform.system() == "Windows" and check_command("certutil"))
    if has_sha:
        results.append(DiagnosticResult("Integrity Hashing", "OK", "sha256 hashing utility available"))
    else:
        results.append(DiagnosticResult("Integrity Hashing", "WARN", "no standard sha256 CLI found", is_warning=True))

    # 5. Domain Verification: Web
    has_node = check_command("node")
    has_playwright = check_command("playwright") or (has_node and check_command("npx"))
    if has_playwright:
        results.append(DiagnosticResult("Web Domain (Playwright)", "OK", "Playwright / Node automation ready"))
    elif has_node:
        results.append(DiagnosticResult("Web Domain (Playwright)", "WARN", "Node.js available, but Playwright not detected", is_warning=True))
    else:
        results.append(DiagnosticResult("Web Domain (Playwright)", "INFO", "Node / Playwright not installed (Web module verification disabled)"))

    # 6. Domain Verification: Multimedia / Video
    has_ffmpeg = check_command("ffmpeg")
    has_ffprobe = check_command("ffprobe")
    if has_ffmpeg and has_ffprobe:
        results.append(DiagnosticResult("Video Domain (ffmpeg)", "OK", "ffmpeg + ffprobe ready"))
    elif has_ffmpeg or has_ffprobe:
        results.append(DiagnosticResult("Video Domain (ffmpeg)", "WARN", "partial ffmpeg toolchain installed", is_warning=True))
    else:
        results.append(DiagnosticResult("Video Domain (ffmpeg)", "INFO", "ffmpeg not installed (Video module verification disabled)"))

    # 7. Domain Verification: 3D / Blender
    has_blender = check_command("blender")
    if has_blender:
        blender_ver = get_command_version("blender", ["--version"])
        results.append(DiagnosticResult("3D Domain (Blender)", "OK", blender_ver))
    else:
        results.append(DiagnosticResult("3D Domain (Blender)", "INFO", "Blender CLI not installed (Blender module verification disabled)"))

    # 8. Workspace Installation State
    ws_checks = []
    cursor_rule = workspace / ".cursor" / "rules" / "uqe.mdc"
    claude_file = workspace / "CLAUDE.md"
    windsurf_rule = workspace / ".windsurf" / "rules" / "uqe.md"
    uqe_dir = workspace / ".uqe"
    installed_targets = []

    if cursor_rule.is_file() and PRIME_DIRECTIVE in cursor_rule.read_text(encoding="utf-8", errors="ignore"):
        installed_targets.append("Cursor (.cursor/rules/uqe.mdc)")
    if claude_file.is_file() and "BEGIN UQE" in claude_file.read_text(encoding="utf-8", errors="ignore"):
        installed_targets.append("Claude (CLAUDE.md)")
    if windsurf_rule.is_file() and PRIME_DIRECTIVE in windsurf_rule.read_text(encoding="utf-8", errors="ignore"):
        installed_targets.append("Windsurf (.windsurf/rules/uqe.md)")

    if installed_targets:
        results.append(DiagnosticResult("UQE Workspace Rules", "OK", f"Active targets: {', '.join(installed_targets)}"))
    else:
        results.append(DiagnosticResult("UQE Workspace Rules", "WARN", f"No active UQE rule found in {workspace}. Run 'uqe init'", is_warning=True))

    if uqe_dir.is_dir():
        modules_count = len(list((uqe_dir / "modules").glob("*.md"))) if (uqe_dir / "modules").is_dir() else 0
        results.append(DiagnosticResult("UQE Runtime Assets", "OK", f".uqe/ present with {modules_count} domain modules"))
    else:
        results.append(DiagnosticResult("UQE Runtime Assets", "INFO", ".uqe/ support directory not present"))

    # Print Report
    print("\n" + "=" * 60)
    print("  UQE DOCTOR -- System & Workspace Diagnostics")
    print("=" * 60)

    has_fatal = False
    for r in results:
        if r.status == "OK":
            icon = "[OK]  "
        elif r.status == "WARN":
            icon = "[WARN]"
        elif r.status == "FAIL":
            icon = "[FAIL]"
            has_fatal = True
        else:
            icon = "[INFO]"
        print(f" {icon}  {r.name:<26} : {r.message}")

    print("=" * 60)
    if has_fatal:
        print(" [!] Critical issues found. Please address FAIL items above.\n")
        return 1
    else:
        print(" [+] System is healthy and ready for verified agent operations.\n")
        return 0
