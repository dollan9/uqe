# TEMPLATE: NEW DOMAIN MODULE

Copy this to `modules/<domain>.md`. Fill Section 2 first — it is the non-negotiable core. Keep the
whole module short (aim ≤ 60 lines): modules are reference depth, not law; SKILL.md stays compact.

## Section 1: Domain & trigger
**Name:** <Domain> · **Load when:** <exact task characteristics that route here> ·
**Skip loading for:** <the T0/T1 cases where reading this file would be over-processing>
**Purpose:** <2–3 sentences: what "done" means here; the characteristic failure mode of agents in
this domain>

## Section 2: Evidence Definition — NON-NEGOTIABLE
What counts as evidence in this domain, per tier:
- T0/T1 cheapest sufficient: <e.g., command output, diff, quoted passage>
- T2 standard: <artifact + how it must be inspected>
- T3 deep: <full package>
State explicitly what does **not** count as evidence here (proxies people mistake for proof).

## Section 3: Verification Pipeline
Step-by-step capture-and-inspect procedure with real commands. Host tools first; name optional
local tools and their fallback behavior when missing.

## Section 4: Common Failure Modes
<5–8 concrete, domain-specific defects — not generic "be careful" advice>

## Section 5: What Cannot Be Verified Here
<Honest limits: which judgments require humans/live environments/other senses>

## Section 6: Stopping Conditions
<How many critique passes at T2/T3; when evidence reuse is acceptable; diminishing-return rule>

## Section 7: Worked Examples
**Good verification:** <one line naming artifacts actually inspected>
**Bad verification:** <one line of the classic fake-confidence shape in this domain>

## Section 8: Registration
1. Add a row to the Module Index table in SKILL.md Section 12 ("load when" wording included).
2. Ensure CI structure check passes (`tests/installer-test.sh` / workflow job 3).
3. No vendor/model names in normative text (Generality rule, CONTRIBUTING.md).
An unregistered module does not exist.
