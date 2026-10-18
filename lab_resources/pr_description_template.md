# Pull Request: Sanctions Screening Integration

## Summary

Adds real-time sanctions screening (`sanctions_check.py`) as a discrete pipeline step between AML analysis and approval, on branch `feature/sanctions-screening`. Delivered end-to-end from Claude Code using MCP-driven analysis, three coordinated sub-agents, and PCI DSS hardening.

## Pipeline Insertion Rationale

<!-- From docs/sanctions_screening_design.md — why this step goes here -->

## Sub-Agent Task Breakdown

| Sub-agent | Responsibility | Output |
|---|---|---|
| sanctions-researcher | Data model recommendation from MCP compliance schema | data model spec |
| code-writer | `sanctions_check.py` implementation + `Skills.md` entry | production code |
| test-generator | `tests/test_sanctions_check.py` | pytest suite |

## Data Model

```json
{"screened": "bool", "match_list": "list", "confidence": "float"}
```

## Test Coverage Summary

- Clean transaction pass
- OFAC match detection
- UN list match detection
- Malformed input handling
- Performance assertion (< 200ms mock)

All tests passing: <!-- yes/no + pytest output -->

## PCI DSS Compliance Attestation

- Input validation applied to all screening inputs
- No plaintext PII (`customer_id`, counterparty name) in logs
- Screening result stored via the encrypted-storage call site
- `/security-review` and PostToolUse bandit hook: zero medium+ findings

## Prompt Caching Strategy

The sanctions-analyst system prompt preamble in the `sanctions_screening` Skill is marked `cache_control: ephemeral` — static across every screening call, reducing per-call latency and token cost at production volume.

## Related Docs

- `docs/sanctions_screening_design.md`
- `CLAUDE.md` → PCI DSS Standards section

## CI Expectation

- `pci-dss-check` — no critical/high findings
- `compliance-scoring` — score ≥ 4/5
