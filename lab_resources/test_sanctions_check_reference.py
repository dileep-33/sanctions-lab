"""
REFERENCE: tests/test_sanctions_check.py for Project 4.
Compare your test-generator sub-agent's output against this — the five
required cases must all be present, mocking _query_sanctions_lists so
results are deterministic.
"""

import time
from unittest.mock import patch

import pytest

from sanctions_check import (
    SanctionsMatch,
    screen_transaction,
)

VALID_CUSTOMER_ID = "CUST-00123"
VALID_COUNTERPARTY = {"name": "Acme Trading Ltd", "country": "US"}
VALID_AMOUNT = 5000.00


def test_clean_transaction_passes_with_no_matches():
    with patch("sanctions_check._query_sanctions_lists", return_value=[]):
        result = screen_transaction(VALID_CUSTOMER_ID, VALID_COUNTERPARTY, VALID_AMOUNT)
    assert result["screened"] is True
    assert result["match_list"] == []
    assert result["confidence"] == 0.0


def test_ofac_match_is_detected():
    mock_match = SanctionsMatch(list_source="OFAC", matched_name="Acme Trading Ltd", score=0.91)
    with patch("sanctions_check._query_sanctions_lists", return_value=[mock_match]):
        result = screen_transaction(VALID_CUSTOMER_ID, VALID_COUNTERPARTY, VALID_AMOUNT)
    assert result["screened"] is True
    assert result["match_list"][0]["list_source"] == "OFAC"
    assert result["confidence"] == pytest.approx(0.91)


def test_un_list_match_is_detected():
    mock_match = SanctionsMatch(list_source="UN", matched_name="Acme Trading Ltd", score=0.83)
    with patch("sanctions_check._query_sanctions_lists", return_value=[mock_match]):
        result = screen_transaction(VALID_CUSTOMER_ID, VALID_COUNTERPARTY, VALID_AMOUNT)
    assert result["screened"] is True
    assert result["match_list"][0]["list_source"] == "UN"
    assert result["confidence"] == pytest.approx(0.83)


@pytest.mark.parametrize(
    "customer_id,counterparty,amount",
    [
        ("", VALID_COUNTERPARTY, VALID_AMOUNT),
        (VALID_CUSTOMER_ID, {}, VALID_AMOUNT),
        (VALID_CUSTOMER_ID, VALID_COUNTERPARTY, -100.0),
    ],
)
def test_malformed_input_is_rejected_gracefully(customer_id, counterparty, amount):
    result = screen_transaction(customer_id, counterparty, amount)
    assert result["screened"] is False
    assert result["match_list"] == []


def test_screening_completes_within_latency_budget():
    with patch("sanctions_check._query_sanctions_lists", return_value=[]):
        start = time.monotonic()
        screen_transaction(VALID_CUSTOMER_ID, VALID_COUNTERPARTY, VALID_AMOUNT)
        elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms < 200, f"Screening took {elapsed_ms:.1f}ms, exceeds 200ms budget"
