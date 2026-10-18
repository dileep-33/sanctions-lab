# Sanctions Screening — Insertion Point & Design

## 1. Pipeline Position

**Current pipeline** (from `compliance/pipeline.py` and `mcp_servers/banking_api/server.py:142-148`):

```
Step 1: kyc_check         → Verify customer identity
Step 2: aml_analysis      → Anti-money laundering screening
Step 3: approval          → Final compliance approval
```

**Proposed pipeline with sanctions screening:**

```
Step 1: kyc_check              → Verify customer identity
Step 2: aml_analysis           → Anti-money laundering screening
Step 3: sanctions_screening    → Check against OFAC/UN/EU sanctions lists [NEW]
Step 4: approval               → Final compliance approval
```

**Rationale for position:**
- **After KYC (Step 1):** Sanctions screening requires verified customer identity to avoid false positives. Must have clean name, address, and ID data.
- **After AML (Step 2):** AML pattern analysis may reveal additional entities (beneficial owners, intermediaries, shell companies) that also require sanctions screening.
- **Before Approval (Step 4):** Sanctions hits are absolute legal prohibitions. Approval logic must not run until sanctions clearance is confirmed.

**Grounded in real implementation:** The pipeline metadata structure (`{"step": int, "name": str, "description": str}`) is returned by `mcp_servers/banking_api/server.py:get_compliance_pipeline()`. Sanctions screening will insert as step 3, incrementing approval to step 4.

---

## 2. Data Inputs Required

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| `customer_id` | string | Transaction context | Yes | Links to customer record from KYC step |
| `counterparty_details` | object | Transaction payload / AML output | Yes | Must include: `name` (string), `country` (ISO 3166-1 alpha-2 code), optional `account_number`, `swift_code` |
| `transaction_amount` | integer | Transaction payload | Yes | Amount in INR. Used for risk-weighting review priority, not for match logic itself |

**ASSUMPTION:** The transaction context object passed between pipeline steps includes these fields. The current `initiate_transfer()` MCP tool (server.py:125-137) returns `{from_account, to_account, amount_inr, reference_id}` but does NOT include counterparty names or country codes. **Integration will require:**
- Adding `counterparty_details` extraction to `initiate_transfer()`
- OR AML module (step 2) enriching transaction context with entity metadata

**ASSUMPTION:** `customer_id` is available from KYC output (step 1). Current code does not show KYC implementation.

---

## 3. Output Schema

```json
{
  "screened": true,
  "match_list": [
    {
      "list_source": "OFAC-SDN",
      "matched_name": "Example Entity LLC",
      "matched_field": "counterparty_name",
      "score": 0.92,
      "list_entry_id": "12345",
      "similarity_basis": "exact_match"
    }
  ],
  "confidence": 0.92,
  "timestamp": "2026-10-18T14:32:54Z",
  "screener_version": "v2.1.0",
  "transaction_reference_id": "TXN-LAB-0001"
}
```

### Field Definitions

- **`screened`** (boolean) — `true` if screening executed successfully, `false` if API/service failure occurred. A `false` value MUST route to manual review.
- **`match_list`** (array) — Zero or more potential sanctions matches. Empty array = no hits.
  - `list_source`: Which sanctions list (e.g., "OFAC-SDN", "UN-1267", "EU-FSF")
  - `matched_name`: The name from the sanctions list that triggered the match
  - `matched_field`: Which input field matched (`customer_name`, `counterparty_name`)
  - `score`: Match confidence score (0.0–1.0)
  - `list_entry_id`: Unique identifier in the source sanctions list
  - `similarity_basis`: Match type (`exact_match`, `fuzzy_match`, `alias_match`, `phonetic_match`)
- **`confidence`** (float, 0.0–1.0) — Overall confidence in the screening result. For multiple matches, this is the highest individual `score`.
- **`timestamp`** (ISO 8601 string) — When screening completed
- **`screener_version`** (string) — Version of sanctions screening service/algorithm used
- **`transaction_reference_id`** (string) — Links back to source transaction for audit trail. Auto-generated if not provided (format: TXN-AUTO-{hash}).

**ASSUMPTION:** Output schema design assumes external sanctions screening API. If implementing in-house, fields like `screener_version` would reference internal module version.

---

## 4. Integration Contract with the AML Module

### Input from AML Module (Step 2 → Step 3)

**AML output structure (ASSUMED — not present in current code):**
```json
{
  "status": "pass" | "flagged" | "fail",
  "risk_score": 0.0–1.0,
  "patterns_detected": ["rapid_movement", "structuring"],
  "enriched_entities": [
    {"type": "beneficial_owner", "name": "...", "country": "..."}
  ]
}
```

**Integration rules:**
1. Sanctions screening runs **independently** of AML verdict. Even if AML status = "pass", sanctions still executes.
2. Sanctions screening reads `enriched_entities` from AML output to screen additional parties identified through pattern analysis.
3. The AML `risk_score` passes through to approval step unchanged.

### Output to Approval Step (Step 3 → Step 4)

**Hard-stop conditions (transaction MUST NOT auto-approve):**
- `screened = false` (service failure) → Manual review
- `match_list` is non-empty AND any match has `score >= 0.75` → Manual compliance review
- `match_list` has 2+ matches with `score >= 0.60` → Manual review (multiple weak signals)

**Pass-through condition:**
- `screened = true` AND `match_list = []` → Proceed to approval step

**ASSUMPTION:** Approval step (step 4) has logic to read `sanctions_screening` output and enforce hard stops. Current code shows approval as metadata only (server.py:147).

### Failure Mode Requirement

**CRITICAL:** If sanctions API is unreachable, network timeout, or internal error:
- MUST set `screened = false`
- MUST route transaction to manual review queue
- NEVER silently pass or skip sanctions check
- Log error to `audit_log/` per CLAUDE.md PCI DSS standards

**Grounded in CLAUDE.md:** Audit logging requirement (section "PCI DSS Standards — MANDATORY", item 4).

---

## 5. Open Questions / Risks

### Name Matching & False Positives
- **Question:** What fuzzy-matching threshold balances false positives vs. regulatory risk?
  - **Context:** Common names (e.g., "Ali Ahmed") appear on sanctions lists and in legitimate customer base. Overly strict matching blocks legitimate transactions; overly loose matching overwhelms manual review queue.
  - **Proposed approach:** Start with `score >= 0.75` as hard stop, collect metrics on false positive rate, tune threshold after 30 days.

### Sanctions List Refresh Cadence
- **Question:** How frequently do we update sanctions list data?
  - **Context:** OFAC updates daily. EU/UN update weekly. Stale data = compliance risk.
  - **Proposed approach:** Daily automated sync at 02:00 UTC. Alert on sync failure. Cache locally for performance but version-stamp all screening results.

### Counterparty Data Availability
- **Open issue:** Current `initiate_transfer()` tool does NOT capture counterparty names or countries (server.py:125-137). Only account IDs.
  - **ASSUMPTION BLOCKER:** Integration requires either:
    1. Modifying `initiate_transfer()` to accept `counterparty_name`, `counterparty_country` as optional params
    2. OR AML module performing entity resolution and populating these fields
  - **Action required:** Clarify with banking-api team which approach to take.

### Performance Impact
- **Risk:** Adding external API call in critical transaction path increases latency.
  - **Mitigation:** Set 500ms timeout for sanctions API. On timeout, mark `screened=false` and route to manual review rather than blocking customer.

### Regulatory Coverage
- **Question:** Which sanctions lists are in scope?
  - **Proposed:** OFAC (US), UN (1267/1988), EU FSF. Excludes country-specific lists (UK HMT, etc.) in Phase 1.
  - **ASSUMPTION:** Customer base is primarily India-based, transactions denominated in INR. US/UN/EU coverage is sufficient for Phase 1 regulatory compliance.

---

## 6. Implementation Notes

**Code locations:**
- Pipeline metadata: `compliance/pipeline.py:get_pipeline_sequence()`
- MCP tool exposure: `mcp_servers/banking_api/server.py:get_compliance_pipeline()`
- **New module (to be created):** `compliance/sanctions_screening.py`

**GROUNDED OBSERVATION:** Current pipeline code is stub implementation (pipeline.py comment line 3: "Module 6 Project 4 adds sanctions screening between AML and approval"). No actual step execution logic exists for kyc_check, aml_analysis, or approval.

**Assumption validation required before implementation:**
1. Confirm transaction data structure passed between pipeline steps
2. Confirm KYC output includes `customer_id` and verified identity fields
3. Confirm AML output includes entity enrichment for counterparty screening
4. Clarify sanctions API provider (external vendor vs. in-house service)
