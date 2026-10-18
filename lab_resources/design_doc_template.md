# Sanctions Screening — Insertion Point & Design

## 1. Pipeline Position

<!-- Where does sanctions screening sit relative to AML analysis and approval? -->

Current pipeline: `kyc_check → aml_analysis → [NEW: sanctions_screening] → approval`

## 2. Data Inputs Required

| Field | Type | Source | Notes |
|---|---|---|---|
| `customer_id` | string | banking-api MCP `get_compliance_pipeline` / sample transactions | Existing customer record lookup |
| `counterparty_details` | object | Transaction payload | `name`, `country`, account/IBAN if available |
| `transaction_amount` | float | Transaction payload | Used for risk-weighting, not match logic |

## 3. Output Schema

```json
{
  "screened": true,
  "match_list": [],
  "confidence": 0.0
}
```

- `screened` (bool) — whether the screening step executed successfully.
- `match_list` (list) — zero or more OFAC/UN matches, each with `list_source`, `matched_name`, `score`.
- `confidence` (float, 0–1) — overall confidence in the screening result.

## 4. Integration Contract with the AML Module

- **Input from AML module:** `aml_result` (status, risk_score) passes through unchanged; sanctions screening runs independently of the AML verdict.
- **Output to Approval step:** any non-empty `match_list` with `confidence >= 0.75` is a hard stop requiring manual compliance review.
- **Failure mode:** if the sanctions API is unreachable, `screened` must be `false` and the transaction routed to manual review — never silently pass.

## 5. Open Questions / Risks

<!-- Fill in during Phase 1 discussion with Claude Code, e.g. false-positive rate,
     name-matching fuzziness, list refresh cadence. -->
