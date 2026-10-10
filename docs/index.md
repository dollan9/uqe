# Universal Quality Engine (UQE) Documentation

Welcome to the official documentation for **UQE (Universal Quality Engine)** — the cognitive operating system for AI agents.

## Core Principle: The Prime Directive

> **Assume nothing. Verify everything. Use the cheapest sufficient evidence. Do not ship blind. Do not fabricate. Do not over-process trivial work.**

Current AI agents generate code, content, and designs without empirical self-verification. They guess user intent, research superficially, and claim success without inspectable evidence.

UQE replaces this with a closed **Quality Loop**:
1. **Decode Intent**: Unpack ambiguity before writing code.
2. **Deep Research**: Cross-reference minimum authoritative sources.
3. **Execute**: Build the solution.
4. **Verify with Evidence**: Inspect rendered screens, test outputs, or diffs.
5. **Adversarial Self-Critique**: Classify defects (Critical, Major, Minor).
6. **Honest Delivery**: Disclose unverified claims with reproduction steps.

---

## Quick Navigation

- [Getting Started](./getting-started.md): 1-line installation, package managers, and setup.
- [CLI Reference](./cli.md): Using `uqe doctor`, `uqe verify`, `uqe report`, and `uqe benchmark`.
- [UQEB Benchmark](./benchmarks.md): Empirical anti-hallucination benchmarks.
- [Domain Modules](./modules.md): Web, Video, 3D/Blender, Research, Code, and Memory modules.
