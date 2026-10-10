# Getting Started with UQE

UQE is designed for **zero-friction adoption** across any modern development environment.

## 1. Quick Installation (One-Liner)

No git cloning required. Run directly in your project root:

### Linux / macOS
```bash
curl -fsSL https://raw.githubusercontent.com/dollan9/uqe/main/install.sh | bash
```

### Windows PowerShell
```powershell
irm https://raw.githubusercontent.com/dollan9/uqe/main/install.ps1 | iex
```

### Node.js / NPX
```bash
npx uqe init
```

### Python / Pip
```bash
pip install uqe && uqe init
```

---

## 2. Supported Agent Targets

UQE auto-detects your workspace environment, but you can also specify your target explicitly:

| Target | Flag | Destination | Activation Mechanism |
| :--- | :--- | :--- | :--- |
| **Cursor** | `--target cursor` | `.cursor/rules/uqe.mdc` | MDC rule front-matter (`alwaysApply: false` by default) |
| **Claude Code** | `--target claude` | `CLAUDE.md` | Marker-delimited block (`<!-- BEGIN UQE -->` ... `<!-- END UQE -->`) |
| **Windsurf** | `--target windsurf`| `.windsurf/rules/uqe.md` | Native rules directory |
| **Copilot / Codex** | `--target codex` | `AGENTS.md` | Marker-delimited block in project root |
| **Gemini CLI** | `--target gemini` | `GEMINI.md` | Marker-delimited block in project root |
| **Generic** | `--target generic` | `.uqe/` | Manual copy into your agent system prompt |

---

## 3. Verify Health

After installing, verify that your agent environment and toolchains are healthy:

```bash
uqe doctor
```

This runs a non-destructive diagnostic check of Python, Git, Playwright, ffmpeg, and active workspace rules.
