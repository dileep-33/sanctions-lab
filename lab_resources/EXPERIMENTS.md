# Project 4 — Experiment Lab

---

## Experiment 1: Break the data-model handoff on purpose

1. Ask the `sanctions-researcher` sub-agent for a data model, but tell the `code-writer` sub-agent to use a *different* field name (e.g. `matches` instead of `match_list`).
2. Run the coordination pass prompt.

**Observe:** Claude Code should flag the mismatch rather than silently reconciling it — this is the point of the explicit coordination step.

---

## Experiment 2: OFAC vs UN precedence

1. Add a counterparty name to the mock data (`_MOCK_OFAC_LIST` and `_MOCK_UN_LIST` in `sanctions_check.py`) that appears on **both** lists with different scores.
2. Run `screen_transaction` against that name.

**Observe:** `confidence` should reflect the higher of the two scores (see `max(... , default=0.0)` in the reference implementation) and `match_list` should contain both entries.

---

## Experiment 3: Hook failure injection

1. Temporarily hardcode a fake API key string in `sanctions_check.py` via Claude Code.
2. Observe the PostToolUse bandit hook output.
3. Remove the line and re-run `/security-review sanctions_check.py` to confirm a clean report.

---

## Experiment 4: Latency budget stress test

```python
import time
from sanctions_check import screen_transaction

start = time.monotonic()
for _ in range(50):
    screen_transaction("CUST-1", {"name": "Acme Trading Ltd", "country": "US"}, 1000)
elapsed = (time.monotonic() - start) / 50 * 1000
print(f"Average: {elapsed:.2f}ms per call")
```

Compare the average against the 200ms budget asserted in `test_screening_completes_within_latency_budget`.

---

## Experiment 5: CI gate failure on purpose

1. Create branch `experiment/sanctions-ci-fail-test`.
2. Add a hardcoded sanctions-API key to `sanctions_check.py`.
3. Open a PR — watch `pci-dss-check` fail.
4. Close the PR without merging.

---

## Extension challenge (+15 min)

**Fail-then-fix CI loop:** open a deliberate PCI violation PR for `sanctions_check.py`, capture the failed gate screenshot, fix it, push again, capture the pass screenshot. Add both to submission evidence.
