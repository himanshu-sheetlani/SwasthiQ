import json
import os
import sys
from unittest.mock import Mock, patch

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.llm_narrative import (
    LLMStructuredResponse,
    TracedFigure,
    format_paise_to_rupees,
    validate_and_extract_traced_figures,
    create_fallback_narrative,
    generate_llm_narrative
)


def test_format_paise_to_rupees():
    """Test formatting paise to rupees."""
    assert format_paise_to_rupees(0) == "₹0.00"
    assert format_paise_to_rupees(100) == "₹1.00"
    assert format_paise_to_rupees(1234) == "₹12.34"
    assert format_paise_to_rupees(123456) == "₹1,234.56"
    assert format_paise_to_rupees(999999) == "₹9,999.99"


def test_traced_figure():
    """Test TracedFigure creation and serialization."""
    fig = TracedFigure("₹1,234.56", "total_billed", 123456)
    result = fig.to_dict()

    assert result["display_value"] == "₹1,234.56"
    assert result["report_field"] == "total_billed"
    assert result["value"] == 123456


def test_llm_structured_response():
    """Test LLMStructuredResponse creation and serialization."""
    fig1 = TracedFigure("₹1,000.00", "total_billed", 100000)
    fig2 = TracedFigure("₹800.00", "total_collected", 80000)
    response = LLMStructuredResponse("Test narrative", [fig1, fig2])
    result = response.to_dict()

    assert result["narrative"] == "Test narrative"
    assert len(result["traced_figures"]) == 2
    assert result["traced_figures"][0]["display_value"] == "₹1,000.00"
    assert result["traced_figures"][1]["display_value"] == "₹800.00"


def test_validate_and_extract_traced_figures_valid():
    """Test validation of valid LLM response."""
    deterministic_report = {
        "total_billed": 100000,
        "total_collected": 80000,
        "peak_business_hour": 14
    }

    llm_response = {
        "narrative": "Test narrative",
        "traced_figures": [
            {
                "display_value": "₹1,000.00",
                "report_field": "total_billed",
                "value": 100000
            },
            {
                "display_value": "₹800.00",
                "report_field": "total_collected",
                "value": 80000
            },
            {
                "display_value": "14:00",
                "report_field": "peak_business_hour",
                "value": 14
            }
        ]
    }

    narrative, traced_figures, errors = validate_and_extract_traced_figures(
        llm_response, deterministic_report
    )

    assert narrative == "Test narrative"
    assert len(traced_figures) == 3
    assert len(errors) == 0
    assert traced_figures[0].display_value == "₹1,000.00"
    assert traced_figures[0].report_field == "total_billed"
    assert traced_figures[0].value == 100000


def test_validate_and_extract_traced_figures_invalid_value():
    """Test validation rejects incorrect traced values."""
    deterministic_report = {
        "total_billed": 100000
    }

    llm_response = {
        "narrative": "Test narrative",
        "traced_figures": [
            {
                "display_value": "₹1,000.00",
                "report_field": "total_billed",
                "value": 200000  # Wrong value
            }
        ]
    }

    narrative, traced_figures, errors = validate_and_extract_traced_figures(
        llm_response, deterministic_report
    )

    assert narrative == ""
    assert len(traced_figures) == 0
    assert len(errors) == 1
    assert "value 200000 does not match report value 100000" in errors[0]


def test_validate_and_extract_traced_figures_missing_field():
    """Test validation rejects missing report fields."""
    deterministic_report = {
        "total_billed": 100000
    }

    llm_response = {
        "narrative": "Test narrative",
        "traced_figures": [
            {
                "display_value": "₹1,000.00",
                "report_field": "nonexistent_field",
                "value": 100000
            }
        ]
    }

    narrative, traced_figures, errors = validate_and_extract_traced_figures(
        llm_response, deterministic_report
    )

    assert narrative == ""
    assert len(traced_figures) == 0
    assert len(errors) == 1
    assert "report_field 'nonexistent_field' not found in deterministic report" in errors[0]


def test_create_fallback_narrative_refund_only():
    """Test fallback narrative for refund-only day."""
    deterministic_report = {
        "reconciliation": {
            "total_billed": 0,
            "total_collected": 0,
            "total_refunds": 49000,
            "outstanding": 0,
            "total_billed_by_mode": {"cash": 0, "card": 0, "upi": 0},
            "total_collected_by_mode": {"cash": 0, "card": 0, "upi": 0},
            "total_refunds_by_mode": {"cash": 0, "card": 24000, "upi": 25000}
        },
        "analytics": {
            "peak_business_hour": 16,  # from the data: peak hour is 16 (4pm)
            "revenue_by_hour": { 10: -24000, 13: -22000, 16: -3000 },
            "top_medicines_by_quantity": [
                {"drug_name": "OMEPRAZOLE", "quantity": 1},
                {"drug_name": "METFORMIN", "quantity": 1},
                {"drug_name": "ATORVASTATIN", "quantity": 2},
                {"drug_name": "AMOXICILLIN", "quantity": 3}
            ],
            "top_medicines_by_revenue": [
                {"drug_name": "METFORMIN", "revenue_paise": -3000},
                {"drug_name": "OMEPRAZOLE", "revenue_paise": -4000},
                {"drug_name": "AMOXICILLIN", "revenue_paise": -18000},
                {"drug_name": "ATORVASTATIN", "revenue_paise": -24000}
            ]
        },
        "visit_count": 3,
        "refund_visit_count": 3
    }

    response = create_fallback_narrative(deterministic_report)

    # Check that the narrative follows the expected format
    assert "Good evening! Here's today's summary for Mehta Clinic" in response.narrative
    assert "₹0 billed across 3 visits, ₹0 collected (0%)." in response.narrative
    assert "₹0 is still outstanding across 0 visits, and ₹490 was refunded on 3 visit(s)." in response.narrative
    assert "Busiest hour: 4pm-5pm, with ₹0 in revenue." in response.narrative
    assert "Top mover by quantity: OMEPRAZOLE (1 units)." in response.narrative
    assert "Top by revenue: METFORMIN (₹-30)." in response.narrative
    assert "Note: cost data wasn't available today, so this is revenue, not profit - flagging rather than estimating." in response.narrative

    # Check traced figures
    dict_response = response.to_dict()
    assert len(dict_response["traced_figures"]) == 5  # All key metrics

    # Find the refunds traced figure
    refund_fig = next((f for f in dict_response["traced_figures"]
                      if f["report_field"] == "total_refunds"), None)
    assert refund_fig is not None
    assert refund_fig["display_value"] == "₹490.00"
    assert refund_fig["value"] == 49000


def test_create_fallback_narrative_empty_day():
    """Test fallback narrative for empty day."""
    deterministic_report = {
        "reconciliation": {
            "total_billed": 0,
            "total_collected": 0,
            "total_refunds": 0,
            "outstanding": 0,
            "total_billed_by_mode": {"cash": 0, "card": 0, "upi": 0},
            "total_collected_by_mode": {"cash": 0, "card": 0, "upi": 0},
            "total_refunds_by_mode": {"cash": 0, "card": 0, "upi": 0}
        },
        "analytics": {
            "peak_business_hour": 0,
            "revenue_by_hour": {},
            "top_medicines_by_quantity": [],
            "top_medicines_by_revenue": []
        },
        "visit_count": 0,
        "refund_visit_count": 0,
        "date_str": "Today"
    }

    response = create_fallback_narrative(deterministic_report)

    # Check that the narrative follows the expected format
    assert "Good evening! Here's today's summary for Mehta Clinic" in response.narrative
    assert "₹0 billed across 0 visits, ₹0 collected (0%)." in response.narrative
    assert "₹0 is still outstanding across 0 visits, and ₹0 was refunded on 0 visit(s)." in response.narrative
    assert "Busiest hour: 12am-1am, with ₹0 in revenue." in response.narrative
    assert "Top mover by quantity: N/A (0 units)." in response.narrative
    assert "Top by revenue: N/A (₹0)." in response.narrative
    assert "Note: cost data wasn't available today, so this is revenue, not profit - flagging rather than estimating." in response.narrative

    # Check traced figures
    dict_response = response.to_dict()
    assert len(dict_response["traced_figures"]) == 5  # billed, collected, refunds, outstanding, peak hour


def test_create_fallback_narrative_normal_day():
    """Test fallback narrative for normal day."""
    deterministic_report = {
        "reconciliation": {
            "total_billed": 319000,
            "total_collected": 317200,
            "total_refunds": 0,
            "outstanding": 1800,
            "total_billed_by_mode": {"cash": 127500, "card": 83500, "upi": 108000},
            "total_collected_by_mode": {"cash": 127000, "card": 82700, "upi": 107500},
            "total_refunds_by_mode": {"cash": 0, "card": 0, "upi": 0}
        },
        "analytics": {
            "peak_business_hour": 13,
            "revenue_by_hour": { 9: 9000, 10: 57000, 11: 33500, 12: 9500, 13: 76000, 14: 3500, 15: 41500, 16: 61000, 17: 22000, 18: 6000 },
            "top_medicines_by_quantity": [
                {"drug_name": "OMEPRAZOLE", "quantity": 18},
                {"drug_name": "METFORMIN", "quantity": 14},
                {"drug_name": "PARACETAMOL", "quantity": 11},
                {"drug_name": "AMOXICILLIN", "quantity": 11},
                {"drug_name": "ATORVASTATIN", "quantity": 10},
                {"drug_name": "PARACETMOL", "quantity": 2}
            ],
            "top_medicines_by_revenue": [
                {"drug_name": "ATORVASTATIN", "revenue_paise": 119357},
                {"drug_name": "OMEPRAZOLE", "revenue_paise": 68735},
                {"drug_name": "AMOXICILLIN", "revenue_paise": 64586},
                {"drug_name": "METFORMIN", "revenue_paise": 41409},
                {"drug_name": "PARACETAMOL", "revenue_paise": 21413},
                {"drug_name": "PARACETMOL", "revenue_paise": 3500}
            ]
        },
        "visit_count": 18,
        "refund_visit_count": 0,
        "date_str": "27 Jul"
    }

    response = create_fallback_narrative(deterministic_report)

    # Check that the narrative follows the expected format
    assert "Good evening! Here's today's summary for Mehta Clinic" in response.narrative
    assert "₹3,190 billed across 18 visits, ₹3,172 collected (99%)." in response.narrative
    assert "₹18 is still outstanding across 0 visits, and ₹0 was refunded on 0 visit(s)." in response.narrative
    assert "Busiest hour: 1pm-2pm, with ₹760 in revenue." in response.narrative
    assert "Top mover by quantity: OMEPRAZOLE (18 units)." in response.narrative
    assert "Top by revenue: ATORVASTATIN (₹1,194)." in response.narrative
    assert "Note: cost data wasn't available today, so this is revenue, not profit - flagging rather than estimating." in response.narrative

    # Check traced figures
    dict_response = response.to_dict()
    traced_fields = [f["report_field"] for f in dict_response["traced_figures"]]
    assert "total_billed" in traced_fields
    assert "total_collected" in traced_fields
    assert "total_refunds" in traced_fields
    assert "outstanding" in traced_fields
    assert "peak_business_hour" in traced_fields

    # Check specific values
    billed_fig = next((f for f in dict_response["traced_figures"]
                      if f["report_field"] == "total_billed"), None)
    assert billed_fig is not None
    assert billed_fig["display_value"] == "₹3,190.00"
    assert billed_fig["value"] == 319000


@patch('app.services.llm_narrative.is_llm_configured')
def test_generate_llm_narrative_not_configured(mock_is_configured):
    """Test fallback when LLM is not configured."""
    mock_is_configured.return_value = False

    deterministic_report = {
        "reconciliation": {
            "total_billed": 100000,
            "total_collected": 80000,
            "total_refunds": 0,
            "outstanding": 20000,
            "total_billed_by_mode": {"cash": 0, "card": 0, "upi": 0},
            "total_collected_by_mode": {"cash": 0, "card": 0, "upi": 0},
            "total_refunds_by_mode": {"cash": 0, "card": 0, "upi": 0}
        },
        "analytics": {
            "peak_business_hour": 10,
            "revenue_by_hour": {},
            "top_medicines_by_quantity": [],
            "top_medicines_by_revenue": []
        },
        "visit_count": 0,
        "refund_visit_count": 0,
        "date_str": "Today"
    }

    response = generate_llm_narrative(deterministic_report)

    # Should use fallback narrative
    assert "Good evening! Here's today's summary for Mehta Clinic" in response.narrative
    assert "₹1,000 billed across 0 visits, ₹800 collected (80%)." in response.narrative
    assert "₹200 is still outstanding across 0 visits, and ₹0 was refunded on 0 visit(s)." in response.narrative
    assert "Busiest hour: 10am-11am, with ₹0 in revenue." in response.narrative
    assert "Top mover by quantity: N/A (0 units)." in response.narrative
    assert "Top by revenue: N/A (₹0)." in response.narrative
    assert "Note: cost data wasn't available today, so this is revenue, not profit - flagging rather than estimating." in response.narrative


if __name__ == "__main__":
    # Run tests
    test_format_paise_to_rupees()
    print("✓ test_format_paise_to_rupees passed")

    test_traced_figure()
    print("✓ test_traced_figure passed")

    test_llm_structured_response()
    print("✓ test_llm_structured_response passed")

    test_validate_and_extract_traced_figures_valid()
    print("✓ test_validate_and_extract_traced_figures_valid passed")

    test_validate_and_extract_traced_figures_invalid_value()
    print("✓ test_validate_and_extract_traced_figures_invalid_value passed")

    test_validate_and_extract_traced_figures_missing_field()
    print("✓ test_validate_and_extract_traced_figures_missing_field passed")

    test_create_fallback_narrative_refund_only()
    print("✓ test_create_fallback_narrative_refund_only passed")

    test_create_fallback_narrative_empty_day()
    print("✓ test_create_fallback_narrative_empty_day passed")

    test_create_fallback_narrative_normal_day()
    print("✓ test_create_fallback_narrative_normal_day passed")

    test_generate_llm_narrative_not_configured()
    print("✓ test_generate_llm_narrative_not_configured passed")

    print("\nAll tests passed! 🎉")