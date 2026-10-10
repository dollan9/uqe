# UQE CLI Reference

The `uqe` command line interface provides a unified toolchain for agent diagnostics, evidence verification, and reporting.

```text
usage: uqe [-h] [--version] {init,doctor,verify,report,benchmark} ...
```

---

## Commands

### `uqe init`
Initializes UQE into the current directory.
```bash
uqe init [--target <auto|cursor|claude|windsurf|codex|gemini|generic>] [--dest <dir>] [--dry-run]
```

### `uqe doctor`
Performs an environmental audit of runtime dependencies and workspace activation.
```bash
uqe doctor [--workspace <path>]
```
- Inspects Python runtime (>= 3.9).
- Inspects Git and sha256 utilities.
- Checks web automation (Playwright/Node), multimedia (ffmpeg/ffprobe), and 3D (Blender).
- Validates active rules and Prime Directive preservation.

### `uqe verify`
Validates an agent's evidence report against `evidence.schema.json` and disk existence checks.
```bash
uqe verify <path/to/evidence.json> [--schema <custom.json>] [--root <workspace>] [--no-file-check]
```

### `uqe report`
Prints an executive terminal summary and generates a standalone, dark-mode HTML dashboard.
```bash
uqe report <path/to/evidence.json> --html <output.html>
```
- Produces a single-file, offline-ready HTML report with score bars, artifact chips, and defect tracking.

### `uqe benchmark`
Runs the official UQEB (Universal Quality Engine Benchmark) test suite.
```bash
uqe benchmark
```
- Tests anti-hallucination gates, SEEN concrete observation rules, memory preservation, and zero-lockin neutrality.
