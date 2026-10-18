# Project 4 — Concepts Deep Dive

## End-to-end agentic delivery flow

```
Claude Code session
    │
    ├─ Phase 1: MCP-driven analysis
    │     banking-api MCP get_compliance_pipeline → docs/sanctions_screening_design.md
    │
    ├─ Phase 2: Sub-agent execution (Task tool)
    │     sanctions-researcher → data model
    │     code-writer         → sanctions_check.py + Skills.md entry
    │     test-generator      → tests/test_sanctions_check.py
    │     coordination pass   → reconcile data model across all three
    │
    ├─ Phase 3: Hardening
    │     /security-review sanctions_check.py
    │     PostToolUse bandit hook → zero medium+ findings
    │     prompt caching (cache_control: ephemeral) on Skills.md entry
    │
    ▼
    Phase 4: GitHub delivery
    │     GitHub MCP create_branch → push_files → create_pull_request
    ▼
GitHub Actions (on pull_request)
    ├─ Job 1: pci-dss-check (bandit + headless claude -p)
    ├─ Job 2: compliance-scoring (Claude-as-Judge 1–5)
    └─ Job 3: gate-summary (both must pass)
```

## Why sub-agents instead of one long prompt

| Concern | Single-agent prompt | Sub-agent decomposition |
|---|---|---|
| Context focus | One context window carries analysis + code + tests | Each sub-agent gets a narrow, well-scoped task |
| Consistency | Easy to drift the data model between design/code/tests | Explicit coordination pass catches mismatches |
| Review | Hard to tell which part came from where | Each phase has an attributable output |

## The three sub-agent roles

| Sub-agent | Input | Output | Failure mode it guards against |
|---|---|---|---|
| `sanctions-researcher` | MCP compliance schema + design doc | Recommended data model | Code written against an ad-hoc, undocumented shape |
| `code-writer` | Researcher's data model | `sanctions_check.py`, `Skills.md` entry | Implementation drifting from the agreed schema |
| `test-generator` | `sanctions_check.py` | `tests/test_sanctions_check.py` | Untested edge cases (malformed input, latency) shipping to prod |

## MCP-driven analysis

Phase 1 does not start from a blank page — it queries the **banking-api MCP server**'s `get_compliance_pipeline` tool to retrieve the *actual* running pipeline sequence (`kyc_check → aml_analysis → approval`) before deciding where sanctions screening fits. This grounds the design doc in the live system rather than assumptions.

## Prompt caching on the new Skill

The `sanctions_screening` Skill's system prompt has a stable "you are a sanctions-compliance analyst" preamble that never changes between calls — only the transaction context varies. Marking that preamble `cache_control: ephemeral` lets every screening call reuse the cached prefix, which matters at the call volume a real-time compliance step sees.

## Hardening loop

`/security-review` (bundled standalone for this project, functionally identical to the Project 2 command) and the PostToolUse bandit hook (bundled from Project 3) both scan `sanctions_check.py`. The gate is: zero medium-or-above bandit findings *and* a clean `/security-review` report before Phase 4.

## CI gate (reused from Project 3)

Same `claude-security-gate.yml` — `pci-dss-check` (headless Claude scans the diff for PCI DSS violations) and `compliance-scoring` (Claude-as-Judge, 1–5, must be ≥ 4) both gate the PR.
