---
description: Scan the current file for PCI DSS violations and output a structured findings report
---

Scan the current file (or the file(s) named in `$ARGUMENTS`) for PCI DSS violations:

- Hardcoded credentials, API keys, or tokens
- Plaintext cardholder data (PAN, CVV) in code, logs, or comments
- Missing input sanitisation on external or MCP-sourced data
- Missing or incomplete audit logging for financial operations
- Encryption gaps for data that should be encrypted at rest or in transit

Output a structured findings report:

```
SECURITY REVIEW: <file>
Findings: <count>
[<SEVERITY>] <requirement> — <description> (line <n>)
  Remediation: <fix>
...
Overall: PASS | FAIL
```

Bundled standalone with this project (Module 6, Project 4) so the lab does not require Project 2 to have been completed first. Functionally identical to the `/security-review` command introduced in Project 2.
