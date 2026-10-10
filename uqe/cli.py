"""
UQE Unified Command Line Interface
"""

import sys
import os
import json
import argparse
import subprocess
import platform
from pathlib import Path

from uqe import __version__
from uqe.doctor import diagnose
from uqe.reporter import generate_html_report
from uqe.benchmark import run_benchmarks

def run_init(args):
    dest = Path(args.dest) if args.dest else Path.cwd()
    repo_root = Path(__file__).resolve().parent.parent

    target = args.target or "auto"
    dry_run = args.dry_run

    print(f"[uqe] Initializing UQE in {dest} (target: {target})...")

    # On Windows prefer install.ps1, on POSIX prefer install.sh
    if platform.system() == "Windows":
        script = repo_root / "install.ps1"
        if script.is_file():
            cmd = [
                "powershell", "-ExecutionPolicy", "Bypass", "-File", str(script),
                "-Target", target, "-Dest", str(dest)
            ]
            if dry_run:
                cmd.append("-DryRun")
            res = subprocess.run(cmd)
            return res.returncode
    else:
        script = repo_root / "install.sh"
        if script.is_file():
            cmd = [str(script), "--target", target, "--dest", str(dest)]
            if dry_run:
                cmd.append("--dry-run")
            res = subprocess.run(cmd)
            return res.returncode

    print(f"[uqe][ERROR] Installer script not found in {repo_root}")
    return 1

def run_verify(args):
    repo_root = Path(__file__).resolve().parent.parent
    val_script = repo_root / "scripts" / "validate_evidence.py"
    if not val_script.is_file():
        # Fallback to local import if present
        sys.path.insert(0, str(repo_root / "scripts"))
        try:
            import validate_evidence
            cmd_args = [args.report]
            if args.schema:
                cmd_args.extend(["--schema", args.schema])
            if args.root:
                cmd_args.extend(["--root", args.root])
            if args.no_file_check:
                cmd_args.append("--no-file-check")
            return validate_evidence.main(cmd_args)
        except ImportError:
            print("[uqe][ERROR] validate_evidence.py script not found.")
            return 1

    cmd = [sys.executable, str(val_script), args.report]
    if args.schema:
        cmd.extend(["--schema", args.schema])
    if args.root:
        cmd.extend(["--root", args.root])
    if args.no_file_check:
        cmd.append("--no-file-check")

    res = subprocess.run(cmd)
    return res.returncode

def run_report(args):
    report_path = Path(args.report)
    if not report_path.is_file():
        print(f"[uqe][ERROR] Evidence report not found: {report_path}")
        return 1

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[uqe][ERROR] Failed to parse evidence report JSON: {e}")
        return 1

    # Terminal summary
    task = data.get("task", "Unknown Task")
    tier = data.get("tier", "T1")
    evidence_items = data.get("evidence", [])
    defects = data.get("defects", [])
    scores = data.get("scores", {})

    print("\n" + "=" * 60)
    print(f"  UQE EVIDENCE REPORT: {task}")
    print(f"  Tier: {tier} | Evidence Items: {len(evidence_items)} | Defects: {len(defects)}")
    print("=" * 60)

    if scores:
        print(" Scores:")
        for k, v in scores.items():
            print(f"   * {k:<20}: {v}/10")

    if defects:
        print("\n Defects:")
        for d in defects:
            print(f"   [{d.get('severity', 'minor').upper()}] {d.get('description')} ({d.get('status', 'open')})")

    if args.html:
        html_out = Path(args.html)
        html_content = generate_html_report(data, title=f"UQE Evidence — {task}")
        html_out.parent.mkdir(parents=True, exist_ok=True)
        html_out.write_text(html_content, encoding="utf-8")
        print(f"\n [+] Standalone HTML dashboard generated at: {html_out.resolve()}")

    print("=" * 60 + "\n")
    return 0

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="uqe",
        description="Universal Quality Engine (UQE) — A cognitive operating system for AI agents."
    )
    parser.add_argument("--version", action="version", version=f"uqe {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize UQE into a project directory")
    init_parser.add_argument("--target", default="auto", choices=["auto", "cursor", "claude", "codex", "gemini", "windsurf", "generic", "manual"])
    init_parser.add_argument("--dest", default="", help="Destination directory (default: current directory)")
    init_parser.add_argument("--dry-run", action="store_true", help="Preview actions without modifying disk")

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Inspect environment and toolchain health")
    doctor_parser.add_argument("--workspace", default="", help="Path to workspace root")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Validate an evidence report against schema")
    verify_parser.add_argument("report", help="Path to evidence JSON report")
    verify_parser.add_argument("--schema", help="Path to custom evidence.schema.json")
    verify_parser.add_argument("--root", help="Workspace root for checking artifact paths")
    verify_parser.add_argument("--no-file-check", action="store_true", help="Skip checking artifact existence on disk")

    # report
    report_parser = subparsers.add_parser("report", help="Generate report summaries and HTML dashboards")
    report_parser.add_argument("report", help="Path to evidence JSON report")
    report_parser.add_argument("--html", help="Output path for standalone HTML dashboard")

    # benchmark
    subparsers.add_parser("benchmark", help="Run empirical UQEB quality & anti-hallucination assertions")

    args = parser.parse_args(argv)

    if args.command == "init":
        return run_init(args)
    elif args.command == "doctor":
        ws = Path(args.workspace) if args.workspace else Path.cwd()
        return diagnose(ws)
    elif args.command == "verify":
        return run_verify(args)
    elif args.command == "report":
        return run_report(args)
    elif args.command == "benchmark":
        repo_root = Path(__file__).resolve().parent.parent
        return run_benchmarks(repo_root)
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
