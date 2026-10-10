# Universal Quality Engine Benchmark (UQEB)

## Objective
The Universal Quality Engine Benchmark (UQEB) provides quantifiable, reproducible metrics to prove that UQE eliminates "AI slop" and stops agents from shipping unverified code.

## The Problem with Standard Agents
| Vector | Standard Agent Behavior | UQE Behavior |
| :--- | :--- | :--- |
| **Completion Claims** | Declares "Done!" with zero proof. | Rejects completion unless backed by inspectable artifacts. |
| **Observation Depth** | Superficial text ("looks good"). | Enforces the SEEN standard (concrete observations >= 10 chars). |
| **Memory Hygiene** | Blindly truncates file headers on token limits. | Isolates structured headers; preserves intent across sessions. |
| **Vendor Neutrality** | Hardcodes specific model names and vendor quirks. | 100% zero-lockin; strictly scanned by CI generality rules. |

## Running the Benchmark
Execute the automated suite locally:
```bash
uqe benchmark
```

All 6 core vectors must achieve 100% pass rates for a compliant UQE runtime.
