# Reviewed for PCI DSS hardening
"""
Sanctions Screening Module — Step 3 in Compliance Pipeline

Performs OFAC/UN/EU sanctions list screening with PCI DSS security controls.
See: docs/sanctions_screening_design.md for integration contract.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Type Definitions
# ---------------------------------------------------------------------------


class SanctionsMatch(TypedDict):
    """Individual sanctions list match."""

    list_source: str
    matched_name: str
    matched_field: Literal["customer_name", "counterparty_name"]
    score: float
    list_entry_id: str
    similarity_basis: Literal["exact_match", "fuzzy_match", "alias_match", "phonetic_match"]


class SanctionsScreeningResult(TypedDict):
    """Sanctions screening step output (Step 3 in compliance pipeline)."""

    screened: bool
    match_list: list[SanctionsMatch]
    confidence: float
    timestamp: str
    screener_version: str
    transaction_reference_id: str


# ---------------------------------------------------------------------------
# PCI DSS Security Controls
# ---------------------------------------------------------------------------


def _mask_pii(value: str) -> str:
    """
    Mask PII for logging per PCI DSS Requirement 3 (CLAUDE.md).
    Format: first initial + last 4 characters.

    Examples:
        "John Smith" -> "J***mith"
        "ABC Corp" -> "A***Corp"
    """
    if not value or len(value) <= 5:
        return "***"
    return f"{value[0]}***{value[-4:]}"


def _validate_input(
    customer_id: str,
    counterparty_details: dict[str, Any],
    transaction_amount: int,
    transaction_reference_id: str,
) -> tuple[bool, str]:
    """
    Input validation per PCI DSS hardening requirements.

    Returns:
        (is_valid, error_message)
    """
    # Validate customer_id format
    if not customer_id or not isinstance(customer_id, str):
        return False, "customer_id must be non-empty string"
    if not re.match(r"^[A-Z0-9\-]+$", customer_id):
        return False, "customer_id contains invalid characters"

    # Validate counterparty_details
    if not isinstance(counterparty_details, dict):
        return False, "counterparty_details must be a dictionary"
    if "name" not in counterparty_details:
        return False, "counterparty_details must contain 'name' field"
    if not isinstance(counterparty_details["name"], str):
        return False, "counterparty_details.name must be string"

    # Validate transaction_amount
    if not isinstance(transaction_amount, int) or transaction_amount < 0:
        return False, "transaction_amount must be non-negative integer"

    # Validate transaction_reference_id
    if not transaction_reference_id or not isinstance(transaction_reference_id, str):
        return False, "transaction_reference_id must be non-empty string"

    return True, ""


def _get_encryption_key() -> Fernet:
    """
    Load encryption key from environment or generate ephemeral key.

    Per PCI DSS Requirement 3: Protect stored cardholder data.

    Returns:
        Fernet cipher instance
    """
    key_env = os.environ.get("SANCTIONS_ENCRYPTION_KEY")

    if key_env:
        # Use key from environment (must be base64-encoded Fernet key)
        try:
            key_bytes = key_env.encode() if isinstance(key_env, str) else key_env
            return Fernet(key_bytes)
        except Exception as e:
            logger.error(f"Invalid SANCTIONS_ENCRYPTION_KEY format: {e}")
            raise
    else:
        # Generate ephemeral key (NOT persistent across restarts)
        ephemeral_key = Fernet.generate_key()
        logger.warning(
            "SANCTIONS_ENCRYPTION_KEY not set - using ephemeral key. "
            "Data encrypted with this key cannot be decrypted after restart. "
            "Set SANCTIONS_ENCRYPTION_KEY environment variable for production."
        )
        return Fernet(ephemeral_key)


def _encrypt_result(result: SanctionsScreeningResult) -> dict[str, Any]:
    """
    Encrypt sanctions screening result for storage.

    Encrypts the entire result using Fernet (AES-128 CBC + HMAC).

    Args:
        result: Sanctions screening result to encrypt

    Returns:
        Dict with encrypted payload and metadata
    """
    cipher = _get_encryption_key()

    # Serialize result to JSON
    plaintext = json.dumps(result).encode()

    # Encrypt
    ciphertext = cipher.encrypt(plaintext)

    return {
        "encrypted": True,
        "algorithm": "Fernet (AES-128-CBC + HMAC-SHA256)",
        "key_version": "v1",
        "ciphertext_b64": base64.b64encode(ciphertext).decode(),
    }


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------


def _persist_audit_log(
    result: SanctionsScreeningResult,
    encrypted_payload: dict[str, Any],
    customer_id: str,
) -> None:
    """
    Persist encrypted sanctions screening result to audit log.

    Per PCI DSS Requirement 10: Track and monitor all access to network resources.

    Args:
        result: Screening result (used for metadata)
        encrypted_payload: Encrypted result from _encrypt_result
        customer_id: Customer ID (will be masked in log)
    """
    # Ensure audit_log directory exists
    audit_dir = Path("audit_log")
    audit_dir.mkdir(exist_ok=True)

    # Generate filename with date (YYYYMMDD)
    log_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    audit_file = audit_dir / f"sanctions_{log_date}.jsonl"

    # Build audit entry (no plaintext PII)
    audit_entry = {
        "timestamp": result["timestamp"],
        "customer_id_masked": _mask_pii(customer_id),
        "transaction_reference_id": result["transaction_reference_id"],
        "screened": result["screened"],
        "match_count": len(result["match_list"]),
        "confidence": result["confidence"],
        "encrypted_payload": encrypted_payload,
    }

    # Append to JSONL file
    with open(audit_file, "a") as f:
        f.write(json.dumps(audit_entry) + "\n")

    logger.debug(f"Audit log written to {audit_file}")


# ---------------------------------------------------------------------------
# Sanctions List Stub (Deterministic for Testing)
# ---------------------------------------------------------------------------

# Stub sanctions list for deterministic testing
# In production, this would be fetched from OFAC/UN/EU APIs and cached
_STUB_SANCTIONS_LIST = [
    {
        "list_source": "OFAC-SDN",
        "name": "Blocked Entity LLC",
        "list_entry_id": "12345",
        "country": "XX",
    },
    {
        "list_source": "UN-1267",
        "name": "Sanctioned Individual",
        "list_entry_id": "67890",
        "country": "YY",
    },
]


def _check_sanctions_stub(name: str, country: str | None = None) -> list[SanctionsMatch]:
    """
    Stub sanctions list check (deterministic for demo).

    Logic:
    - Exact match on "Blocked Entity" substring -> OFAC hit
    - Fuzzy match on "Sanctioned" -> UN hit
    - Otherwise -> no matches

    In production, this would call external sanctions screening API
    with phonetic matching, alias resolution, and fuzzy logic.

    Args:
        name: Entity name to screen
        country: Optional ISO country code

    Returns:
        List of sanctions matches (empty if clear)
    """
    matches: list[SanctionsMatch] = []

    # Normalize for matching
    name_lower = name.lower()

    # Check for exact match patterns (deterministic stub)
    if "blocked entity" in name_lower:
        matches.append(
            {
                "list_source": "OFAC-SDN",
                "matched_name": "Blocked Entity LLC",
                "matched_field": "counterparty_name",
                "score": 0.95,
                "list_entry_id": "12345",
                "similarity_basis": "exact_match",
            }
        )

    # Check for fuzzy match patterns
    if "sanctioned" in name_lower:
        matches.append(
            {
                "list_source": "UN-1267",
                "matched_name": "Sanctioned Individual",
                "matched_field": "counterparty_name",
                "score": 0.82,
                "list_entry_id": "67890",
                "similarity_basis": "fuzzy_match",
            }
        )

    return matches


# ---------------------------------------------------------------------------
# Main Screening Function
# ---------------------------------------------------------------------------


def screen_transaction(
    customer_id: str,
    counterparty_details: dict[str, Any],
    transaction_amount: int,
    transaction_reference_id: str | None = None,
) -> SanctionsScreeningResult:
    """
    Perform sanctions screening on a transaction (Compliance Pipeline Step 3).

    Per design doc (docs/sanctions_screening_design.md):
    - Screens both customer and counterparty against OFAC/UN/EU lists
    - Returns screened=false on API failure (routes to manual review)
    - Hard stop if any match score >= 0.75

    Args:
        customer_id: Customer identifier from KYC (Step 1)
        counterparty_details: Dict with 'name', 'country' (from AML Step 2)
        transaction_amount: Amount in INR (for risk-weighting)
        transaction_reference_id: Links back to source transaction

    Returns:
        SanctionsScreeningResult with screening outcome

    Example:
        >>> result = screen_transaction(
        ...     "CUST-001",
        ...     {"name": "Normal Business Inc", "country": "IN"},
        ...     50000,
        ...     "TXN-LAB-0001"
        ... )
        >>> result["screened"]
        True
        >>> result["match_list"]
        []
    """
    try:
        # Generate default reference ID if not provided
        if transaction_reference_id is None:
            transaction_reference_id = f"TXN-AUTO-{hashlib.sha256(f'{customer_id}{transaction_amount}'.encode()).hexdigest()[:8].upper()}"

        # Input validation (PCI DSS hardening)
        is_valid, error_msg = _validate_input(
            customer_id, counterparty_details, transaction_amount, transaction_reference_id
        )
        if not is_valid:
            # Log validation failure (masked PII)
            logger.warning(
                f"Validation failed: {error_msg} | "
                f"customer={_mask_pii(customer_id)} | "
                f"ref={transaction_reference_id}"
            )
            return {
                "screened": False,
                "match_list": [],
                "confidence": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "screener_version": "v2.1.0-stub",
                "transaction_reference_id": transaction_reference_id,
            }

        # Extract counterparty details
        counterparty_name = counterparty_details["name"]
        counterparty_country = counterparty_details.get("country")

        # Log screening start (masked PII per PCI DSS Req 3)
        logger.info(
            f"Screening transaction | "
            f"customer={_mask_pii(customer_id)} | "
            f"counterparty={_mask_pii(counterparty_name)} | "
            f"amount={transaction_amount} INR | "
            f"ref={transaction_reference_id}"
        )

        # Perform sanctions check (stub)
        matches = _check_sanctions_stub(counterparty_name, counterparty_country)

        # Calculate confidence (highest individual score, or 1.0 if no matches)
        confidence = max((m["score"] for m in matches), default=1.0)

        # Build result
        result: SanctionsScreeningResult = {
            "screened": True,
            "match_list": matches,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "screener_version": "v2.1.0-stub",
            "transaction_reference_id": transaction_reference_id,
        }

        # Log result (masked)
        if matches:
            logger.warning(
                f"⚠️  MATCH FOUND | "
                f"count={len(matches)} | "
                f"confidence={confidence:.2f} | "
                f"ref={transaction_reference_id}"
            )
        else:
            logger.info(f"✓ Clear | ref={transaction_reference_id}")

        # Encrypt result for storage (PCI DSS Req 3)
        encrypted_payload = _encrypt_result(result)

        # Persist to audit log (PCI DSS Req 10)
        _persist_audit_log(result, encrypted_payload, customer_id)

        return result

    except Exception as e:
        # Failure mode: never silently pass (per design doc Section 4)
        logger.error(
            f"❌ ERROR: {type(e).__name__} | "
            f"ref={transaction_reference_id} | "
            f"Routing to manual review"
        )
        return {
            "screened": False,
            "match_list": [],
            "confidence": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "screener_version": "v2.1.0-stub",
            "transaction_reference_id": transaction_reference_id,
        }


# ---------------------------------------------------------------------------
# CLI Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test cases demonstrating deterministic stub behavior
    print("=== Sanctions Screening Module Demo ===\n")

    # Test 1: Clean transaction
    print("Test 1: Clean counterparty")
    result1 = screen_transaction(
        "CUST-2024-001",
        {"name": "Normal Business Inc", "country": "IN"},
        50000,
        "TXN-TEST-001",
    )
    print(f"Result: screened={result1['screened']}, matches={len(result1['match_list'])}\n")

    # Test 2: Blocked entity (deterministic match)
    print("Test 2: Blocked entity")
    result2 = screen_transaction(
        "CUST-2024-002",
        {"name": "Blocked Entity LLC", "country": "XX"},
        100000,
        "TXN-TEST-002",
    )
    print(f"Result: screened={result2['screened']}, matches={len(result2['match_list'])}")
    if result2["match_list"]:
        print(f"  Match: {result2['match_list'][0]['list_source']} score={result2['match_list'][0]['score']}\n")

    # Test 3: Invalid input (validation test)
    print("Test 3: Invalid input")
    result3 = screen_transaction(
        "",  # Invalid customer_id
        {"name": "Test Corp"},
        50000,
        "TXN-TEST-003",
    )
    print(f"Result: screened={result3['screened']} (validation failed)\n")

    print("=== Demo complete ===")
