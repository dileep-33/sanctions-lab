"""
Test suite for sanctions screening module.

Tests cover:
- Clean transaction pass-through
- OFAC match detection
- UN sanctions list match detection
- Malformed input handling
- Performance (latency assertion)
"""

import time
from typing import Any

import pytest

from sanctions_check import screen_transaction


class TestSanctionsScreening:
    """Test suite for sanctions screening functionality."""

    def test_clean_transaction_pass(self) -> None:
        """
        Test that clean transactions with no sanctions matches pass through.

        Expected: screened=True, empty match_list, confidence=1.0
        """
        result = screen_transaction(
            customer_id="CUST-2024-001",
            counterparty_details={"name": "Normal Business Inc", "country": "IN"},
            transaction_amount=50000,
            transaction_reference_id="TXN-TEST-CLEAN-001",
        )

        assert result["screened"] is True, "Clean transaction should be screened successfully"
        assert result["match_list"] == [], "Clean transaction should have no matches"
        assert result["confidence"] == 1.0, "Clean transaction should have confidence 1.0"
        assert result["transaction_reference_id"] == "TXN-TEST-CLEAN-001"
        assert "timestamp" in result
        assert "screener_version" in result

    def test_ofac_match_detection(self) -> None:
        """
        Test OFAC-SDN sanctions list match detection.

        Expected: Match triggered by "Blocked Entity" in counterparty name.
        """
        result = screen_transaction(
            customer_id="CUST-2024-002",
            counterparty_details={"name": "Blocked Entity LLC", "country": "XX"},
            transaction_amount=100000,
            transaction_reference_id="TXN-TEST-OFAC-001",
        )

        assert result["screened"] is True, "OFAC check should complete successfully"
        assert len(result["match_list"]) == 1, "Should detect exactly one OFAC match"

        match = result["match_list"][0]
        assert match["list_source"] == "OFAC-SDN", "Match should be from OFAC-SDN list"
        assert match["matched_name"] == "Blocked Entity LLC"
        assert match["matched_field"] == "counterparty_name"
        assert match["score"] == 0.95, "OFAC exact match should have score 0.95"
        assert match["similarity_basis"] == "exact_match"
        assert match["list_entry_id"] == "12345"

        assert result["confidence"] == 0.95, "Confidence should match highest score"
        assert result["transaction_reference_id"] == "TXN-TEST-OFAC-001"
        assert "timestamp" in result
        assert "screener_version" in result

    def test_un_list_match_detection(self) -> None:
        """
        Test UN-1267 sanctions list match detection.

        Expected: Match triggered by "Sanctioned" in counterparty name.
        """
        result = screen_transaction(
            customer_id="CUST-2024-003",
            counterparty_details={"name": "Sanctioned Individual Corp", "country": "YY"},
            transaction_amount=75000,
            transaction_reference_id="TXN-TEST-UN-001",
        )

        assert result["screened"] is True, "UN check should complete successfully"
        assert len(result["match_list"]) == 1, "Should detect exactly one UN match"

        match = result["match_list"][0]
        assert match["list_source"] == "UN-1267", "Match should be from UN-1267 list"
        assert match["matched_name"] == "Sanctioned Individual"
        assert match["matched_field"] == "counterparty_name"
        assert match["score"] == 0.82, "UN fuzzy match should have score 0.82"
        assert match["similarity_basis"] == "fuzzy_match"
        assert match["list_entry_id"] == "67890"

        assert result["confidence"] == 0.82, "Confidence should match highest score"
        assert result["transaction_reference_id"] == "TXN-TEST-UN-001"
        assert "timestamp" in result
        assert "screener_version" in result

    def test_malformed_input_handling(self) -> None:
        """
        Test that malformed inputs are handled safely with screened=False.

        Tests multiple invalid input scenarios per PCI DSS hardening.
        """
        # Test 1: Empty customer_id
        result1 = screen_transaction(
            customer_id="",
            counterparty_details={"name": "Valid Corp", "country": "IN"},
            transaction_amount=50000,
            transaction_reference_id="TXN-TEST-INVALID-001",
        )
        assert result1["screened"] is False, "Empty customer_id should fail validation"
        assert result1["match_list"] == [], "Failed validation should return empty match list"

        # Test 2: Missing counterparty name
        result2 = screen_transaction(
            customer_id="CUST-2024-004",
            counterparty_details={"country": "IN"},  # Missing 'name' field
            transaction_amount=50000,
            transaction_reference_id="TXN-TEST-INVALID-002",
        )
        assert result2["screened"] is False, "Missing counterparty name should fail validation"

        # Test 3: Negative transaction amount
        result3 = screen_transaction(
            customer_id="CUST-2024-005",
            counterparty_details={"name": "Valid Corp", "country": "IN"},
            transaction_amount=-1000,  # Negative amount
            transaction_reference_id="TXN-TEST-INVALID-003",
        )
        assert result3["screened"] is False, "Negative amount should fail validation"

        # Test 4: Invalid customer_id format (special chars)
        result4 = screen_transaction(
            customer_id="CUST@2024!",  # Invalid characters
            counterparty_details={"name": "Valid Corp", "country": "IN"},
            transaction_amount=50000,
            transaction_reference_id="TXN-TEST-INVALID-004",
        )
        assert result4["screened"] is False, "Invalid customer_id format should fail validation"

    def test_latency_assertion(self) -> None:
        """
        Test that sanctions screening completes within performance SLA.

        Expected: Execution time < 200ms per design doc performance requirements.
        """
        start_time = time.perf_counter()

        result = screen_transaction(
            customer_id="CUST-2024-PERF-001",
            counterparty_details={"name": "Performance Test Corp", "country": "US"},
            transaction_amount=50000,
            transaction_reference_id="TXN-TEST-PERF-001",
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert result["screened"] is True, "Performance test should complete successfully"
        assert elapsed_ms < 200, f"Screening should complete in <200ms, took {elapsed_ms:.2f}ms"

    def test_optional_transaction_reference_id(self) -> None:
        """
        Test that transaction_reference_id parameter is optional and auto-generated.

        Expected: Auto-generated ID when not provided.
        """
        result = screen_transaction(
            customer_id="CUST-2024-006",
            counterparty_details={"name": "Auto ID Test Corp", "country": "IN"},
            transaction_amount=25000,
            # transaction_reference_id not provided
        )

        assert result["screened"] is True
        assert result["transaction_reference_id"].startswith("TXN-AUTO-"), "Should auto-generate reference ID"
        assert len(result["transaction_reference_id"]) > 10, "Auto-generated ID should have sufficient entropy"

    def test_multiple_sanctions_matches(self) -> None:
        """
        Test handling of counterparty matching multiple sanctions lists.

        Expected: Both OFAC and UN matches detected if name contains both keywords.
        """
        result = screen_transaction(
            customer_id="CUST-2024-007",
            counterparty_details={"name": "Blocked Entity Sanctioned Corp", "country": "XX"},
            transaction_amount=200000,
            transaction_reference_id="TXN-TEST-MULTI-001",
        )

        assert result["screened"] is True
        assert len(result["match_list"]) == 2, "Should detect both OFAC and UN matches"

        # Verify both lists are represented
        list_sources = {match["list_source"] for match in result["match_list"]}
        assert "OFAC-SDN" in list_sources, "Should include OFAC match"
        assert "UN-1267" in list_sources, "Should include UN match"

        # Confidence should be the highest individual score
        assert result["confidence"] == 0.95, "Confidence should be max(0.95, 0.82) = 0.95"


# Run tests with: pytest tests/test_sanctions_check.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
