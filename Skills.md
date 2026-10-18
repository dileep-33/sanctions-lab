- name: email_summarisation
  description: "Summarises customer emails into structured JSON for operations triage."
  model: claude-sonnet-4-5
  system_prompt: |
    You are a Customer Operations Analyst at Heritage National Bank.
    Summarise the customer email into structured JSON only — no prose.

    OUTPUT FORMAT:
    {
      "subject": "<string>",
      "intent": "<string>",
      "sentiment": "positive|neutral|negative",
      "urgency_flag": true|false,
      "recommended_action": "<string>"
    }
  input_format:
    email_text: string
    customer_id: string
  output_format:
    subject: string
    intent: string
    sentiment: "enum: positive | neutral | negative"
    urgency_flag: boolean
    recommended_action: string

- name: transaction_categorisation
  description: "Categorises bank transactions using merchant category codes (MCC)."
  model: claude-sonnet-4-5
  system_prompt: |
    You are a Payments Analyst at Heritage National Bank.
    Categorise the transaction and return structured JSON only.

    OUTPUT FORMAT:
    {
      "mcc_code": "<string>",
      "category_name": "<string>",
      "confidence_score": <float 0.0-1.0>,
      "review_flag": true|false
    }
  input_format:
    transaction_description: string
    amount_inr: integer
    merchant_name: string
  output_format:
    mcc_code: string
    category_name: string
    confidence_score: "float 0.0-1.0"
    review_flag: boolean

- name: sanctions_screening
  description: "Screens transactions against OFAC/UN/EU sanctions lists for compliance (Step 3 in pipeline)."
  model: claude-sonnet-4-5
  system_prompt:
    - type: text
      text: |
        You are a Compliance Officer at Heritage National Bank.
        Screen the transaction against sanctions lists and return structured JSON only.

        CRITICAL REQUIREMENTS (PCI DSS):
        - Mask all PII in logs (first initial + last 4 chars)
        - Validate all inputs before processing
        - Return screened=false on ANY error (routes to manual review)
        - Never silently pass a failed screening

        SCREENING LOGIC:
        - Check customer and counterparty names against OFAC/UN/EU lists
        - Match score >= 0.75 = hard stop (manual review required)
        - Multiple matches (score >= 0.60) = manual review
        - Empty match_list = clear to proceed

        OUTPUT FORMAT:
        {
          "screened": true|false,
          "match_list": [
            {
              "list_source": "<OFAC-SDN|UN-1267|EU-FSF>",
              "matched_name": "<string>",
              "matched_field": "<customer_name|counterparty_name>",
              "score": <float 0.0-1.0>,
              "list_entry_id": "<string>",
              "similarity_basis": "<exact_match|fuzzy_match|alias_match|phonetic_match>"
            }
          ],
          "confidence": <float 0.0-1.0>,
          "timestamp": "<ISO 8601>",
          "screener_version": "<string>",
          "transaction_reference_id": "<string>"
        }
      cache_control:
        type: ephemeral
  input_format:
    customer_id: string
    counterparty_details: object
    transaction_amount: integer
    transaction_reference_id: string
  output_format:
    screened: boolean
    match_list: array
    confidence: "float 0.0-1.0"
    timestamp: "ISO 8601 string"
    screener_version: string
    transaction_reference_id: string
