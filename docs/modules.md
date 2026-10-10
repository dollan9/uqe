# UQE Domain & Behavioral Modules

UQE is modular by design. While `SKILL.md` acts as the Universal Brain and router, specific domain expectations are governed by individual contracts in `modules/`:

| Module | Scope | Key Evidence Requirement |
| :--- | :--- | :--- |
| **`web.md`** | Web applications & UI | Responsive screenshots at 1440/768/375px, console logs, a11y audit |
| **`video.md`** | Video & Motion | Keyframe extraction, ffprobe metadata, audio loudness (EBU R128) |
| **`blender.md`** | 3D modeling | Headless render, manifold edge verification, degenerate face check |
| **`research.md`** | Analysis & fact-finding | Minimum 3 primary sources, citation verification, counter-evidence search |
| **`code.md`** | Software engineering | Automated test execution, type checks, lint runs, zero mock placeholders |
| **`writing.md`** | Editorial & copywriting | Readability score, tone consistency, fact checking |
| **`security.md`** | Safety & secrets | Secret scanning, injection defense, privilege escalation audit |
| **`evidence.md`** | Evidence ledger contract | E1/E2/E3 hierarchy, SEEN standard, inspectable artifact paths |
| **`memory.md`** | Preferences & lessons | Non-destructive updates, token budget pruning, header preservation |
| **`routing.md`** | Domain classification | Deterministic domain match, zero ambiguous cross-routing |
| **`feedback.md`** | User alignment | Structured clarification prompts, non-assumptive preference updates |
| **`learning.md`** | Self-improvement | Post-session lesson distillation, recurring mistake avoidance |
| **`general.md`** | General operations | Baseline verification, sanity tests, honest error reporting |
