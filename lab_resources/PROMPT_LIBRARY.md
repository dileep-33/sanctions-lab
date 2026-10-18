# Project 4 — Prompt Library

---

## Phase 1 — Analysis

### Retrieve pipeline + sample transactions

```
Using the banking-api MCP server, call get_compliance_pipeline and show me
the current compliance pipeline sequence. Then show a sample transaction
so I can see the shape of the data flowing between steps.
```

### Identify insertion point

```
Based on the pipeline above, where exactly should a sanctions-screening
step be inserted between aml_analysis and approval? Justify the position.
```

### Draft the design doc

```
Using lab_resources/design_doc_template.md as the skeleton, write
docs/sanctions_screening_design.md documenting: the pipeline insertion
position, data inputs required (customer_id, counterparty_details,
transaction_amount), the output schema (screened: bool, match_list: list,
confidence: float), and the integration contract with the AML module.
```

---

## Phase 2 — Sub-Agents

### 1. sanctions-researcher

```
Spawn a sub-agent named "sanctions-researcher". Its task:
1. Query the banking-api MCP server for existing compliance data structures.
2. Cross-reference docs/sanctions_screening_design.md.
3. Return a recommended data model for the sanctions check result,
   consistent with {screened: bool, match_list: list, confidence: float}.
Return only the data model and a one-paragraph rationale.
```

### 2. code-writer

```
Spawn a sub-agent named "code-writer". Its task:
1. Take the data model from sanctions-researcher.
2. Implement sanctions_check.py, stubbing the OFAC/UN sanctions list API
   call deterministically, and applying PCI DSS hardening (input
   validation, no plaintext PII in logs, encrypted result storage).
3. Append a sanctions_screening skill entry to Skills.md, matching the
   existing schema (name, description, system_prompt, input_format,
   output_format, model), with cache_control: ephemeral on the stable
   system prompt preamble.
Flag any conflict with the design doc's schema instead of silently
choosing one.
```

### 3. test-generator

```
Spawn a sub-agent named "test-generator". Its task:
Write tests/test_sanctions_check.py covering: clean transaction pass,
OFAC match detection, UN list match detection, malformed input handling,
and a performance assertion (response < 200ms on mock). Mock the
sanctions API call so tests are deterministic. Run the suite and report
pass/fail for each case.
```

### 4. Coordination pass

```
Review the outputs from sanctions-researcher, code-writer, and
test-generator together. Confirm the data model is identical across the
design doc, sanctions_check.py, and the test suite. Flag and resolve any
mismatch before proceeding to Phase 3.
```

---

## Phase 3 — Hardening

```
/security-review sanctions_check.py
```

```
Apply Module 5-style prompt caching to the sanctions_screening skill's
system prompt preamble in Skills.md: wrap the stable analyst instructions
in {"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}.
```

---

## Phase 4 — GitHub Delivery

```
Using the GitHub MCP server, create a new branch feature/sanctions-screening.
```

```
Use GitHub MCP push_files to commit sanctions_check.py,
tests/test_sanctions_check.py, the updated Skills.md, and
docs/sanctions_screening_design.md to feature/sanctions-screening.
```

```
Create a pull request to main using GitHub MCP. Use
lab_resources/pr_description_template.md as the skeleton — fill in the
pipeline insertion rationale, sub-agent task breakdown, data model, test
coverage summary, PCI DSS attestation, and caching strategy.
```
