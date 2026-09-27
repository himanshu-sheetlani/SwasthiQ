import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.core.llm_config import get_llm_config, is_llm_configured

logger = logging.getLogger(__name__)


class TracedFigure:
    def __init__(self, display_value: str, report_field: str, value: Any):
        self.display_value = display_value
        self.report_field = report_field
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display_value": self.display_value,
            "report_field": self.report_field,
            "value": self.value
        }


class LLMStructuredResponse:
    def __init__(self, narrative: str, traced_figures: List[TracedFigure], source: str = "llm"):
        self.narrative = narrative
        self.traced_figures = traced_figures
        self.source = source  # "llm" or "fallback"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "narrative": self.narrative,
            "traced_figures": [figure.to_dict() for figure in self.traced_figures],
            "source": self.source
        }


def format_paise_to_rupees(paise: int) -> str:
    """Convert paise to rupees format for display."""
    rupees = paise / 100
    return f"₹{rupees:,.2f}"


def validate_and_extract_traced_figures(
    llm_response: Dict[str, Any],
    deterministic_report: Dict[str, Any]
) -> Tuple[str, List[TracedFigure], List[str]]:
    """
    Validate LLM response and extract traced figures.
    Returns (narrative, traced_figures, errors)
    """
    errors = []

    # Validate schema
    if not isinstance(llm_response, dict):
        errors.append("LLM response is not a dictionary")
        return "", [], errors

    if "narrative" not in llm_response:
        errors.append("Missing 'narrative' field in LLM response")
        return "", [], errors

    if "traced_figures" not in llm_response:
        errors.append("Missing 'traced_figures' field in LLM response")
        return "", [], errors

    narrative = llm_response["narrative"]
    if not isinstance(narrative, str):
        errors.append("'narrative' field must be a string")
        return "", [], errors

    traced_figures_data = llm_response["traced_figures"]
    if not isinstance(traced_figures_data, list):
        errors.append("'traced_figures' field must be a list")
        return narrative, [], errors

    traced_figures = []

    # Define the fields we expect to trace from the report
    # Mapping from report field to display label and conversion function
    traceable_fields = {
        "total_billed": ("Total Billed", format_paise_to_rupees),
        "total_collected": ("Total Collected", format_paise_to_rupees),
        "total_refunds": ("Total Refunds", format_paise_to_rupees),
        "outstanding": ("Outstanding Amount", format_paise_to_rupees),
        "peak_business_hour": ("Peak Business Hour", lambda x: f"{x}:00"),
    }

    # Process each traced figure
    for idx, fig_data in enumerate(traced_figures_data):
        if not isinstance(fig_data, dict):
            errors.append(f"Traced figure {idx} is not a dictionary")
            continue

        # Check required fields
        required_fields = ["display_value", "report_field", "value"]
        for field in required_fields:
            if field not in fig_data:
                errors.append(f"Traced figure {idx} missing required field '{field}'")
                break
        else:
            display_value = fig_data["display_value"]
            report_field = fig_data["report_field"]
            value = fig_data["value"]

            # Validate that the report_field exists in deterministic report
            if report_field not in deterministic_report:
                errors.append(f"Traced figure {idx}: report_field '{report_field}' not found in deterministic report")
                continue

            # Validate that the value matches the report value
            report_value = deterministic_report[report_field]
            if value != report_value:
                errors.append(
                    f"Traced figure {idx}: value {value} does not match report value {report_value} for field '{report_field}'"
                )
                continue

            # Create traced figure
            traced_figures.append(TracedFigure(display_value, report_field, value))

    # If there are any errors in traced figures, reject the entire traced figures set and return empty narrative
    if errors:
        return "", [], errors

    return narrative, traced_figures, errors


def format_rupees_no_symbol(paise: int) -> str:
    """Convert paise to rupees string with commas, no ₹ symbol, rounded to nearest rupee."""
    rupees = round(paise / 100)
    return f"{rupees:,}"

def format_hour_12(hour: int) -> str:
    """Convert hour (0-23) to 12-hour format string like '12am', '1pm', etc."""
    if hour == 0:
        return "12am"
    elif hour < 12:
        return f"{hour}am"
    elif hour == 12:
        return "12pm"
    else:
        return f"{hour-12}pm"

def create_fallback_narrative(deterministic_report: Dict[str, Any]) -> LLMStructuredResponse:
    """Create a fallback narrative when LLM is not available or fails."""
    reconciliation = deterministic_report.get("reconciliation", {})
    analytics = deterministic_report.get("analytics", {})
    visit_count = deterministic_report.get("visit_count", 0)
    refund_visit_count = deterministic_report.get("refund_visit_count", 0)
    date_str = deterministic_report.get("date_str", "Today")

    # Extract key metrics
    total_billed = reconciliation.get("total_billed", 0)
    total_collected = reconciliation.get("total_collected", 0)
    total_refunds = reconciliation.get("total_refunds", 0)
    outstanding = reconciliation.get("outstanding", 0)
    peak_hour = analytics.get("peak_business_hour", 0)
    revenue_by_hour = analytics.get("revenue_by_hour", {})
    top_medicines_by_quantity = analytics.get("top_medicines_by_quantity", [])
    top_medicines_by_revenue = analytics.get("top_medicines_by_revenue", [])

    # Format for display (rupees with commas)
    total_billed_rs = format_rupees_no_symbol(total_billed)
    total_collected_rs = format_rupees_no_symbol(total_collected)
    total_refunds_rs = format_rupees_no_symbol(total_refunds)
    outstanding_rs = format_rupees_no_symbol(outstanding)

    # Collection percentage
    collection_pct = 0
    if total_billed > 0:
        collection_pct = int((total_collected * 100) / total_billed)

    # Outstanding visit count (approx: we don't have per-visit outstanding, set to 0)
    outstanding_visit_count = 0  # placeholder

    # Peak hour formatting
    if peak_hour is not None:
        peak_hour_str = format_hour_12(peak_hour)
        next_hour = (peak_hour + 1) % 24
        next_hour_str = format_hour_12(next_hour)
        peak_hour_range = f"{peak_hour_str}-{next_hour_str}"
        peak_revenue_paise = revenue_by_hour.get(peak_hour, 0)
        # Show revenue as non-negative (if negative, show 0)
        peak_revenue_paise_display = max(0, peak_revenue_paise)
        peak_revenue_rs = format_rupees_no_symbol(peak_revenue_paise_display)
    else:
        peak_hour_range = "N/A"
        peak_revenue_rs = "0"

    # Top medicine by quantity
    if top_medicines_by_quantity:
        top_med_qty_name = top_medicines_by_quantity[0].get("drug_name", "")
        top_med_qty = top_medicines_by_quantity[0].get("quantity", 0)
    else:
        top_med_qty_name = "N/A"
        top_med_qty = 0

    # Top medicine by revenue
    if top_medicines_by_revenue:
        top_med_rev_name = top_medicines_by_revenue[0].get("drug_name", "")
        top_med_rev_paise = top_medicines_by_revenue[0].get("revenue_paise", 0)
        top_med_rev_rs = format_rupees_no_symbol(top_med_rev_paise)
    else:
        top_med_rev_name = "N/A"
        top_med_rev_rs = "0"

    # Build narrative exactly as requested
    narrative = f"""Good evening! Here's today's summary for Mehta Clinic ({date_str}):

₹{total_billed_rs} billed across {visit_count} visits, ₹{total_collected_rs} collected ({collection_pct}%).
₹{outstanding_rs} is still outstanding across {outstanding_visit_count} visits, and ₹{total_refunds_rs} was refunded on {refund_visit_count} visit(s).

Busiest hour: {peak_hour_range}, with ₹{peak_revenue_rs} in revenue.

Top mover by quantity: {top_med_qty_name} ({top_med_qty} units).
Top by revenue: {top_med_rev_name} (₹{top_med_rev_rs}).

Note: cost data wasn't available today, so this is revenue, not profit - flagging rather than estimating."""

    # Create traced figures (keep the same as before for consistency)
    traced_figures = []

    # Add traced figures for key metrics
    if "total_billed" in reconciliation:
        traced_figures.append(TracedFigure(
            format_paise_to_rupees(total_billed), "total_billed", total_billed
        ))

    if "total_collected" in reconciliation:
        traced_figures.append(TracedFigure(
            format_paise_to_rupees(total_collected), "total_collected", total_collected
        ))

    if "total_refunds" in reconciliation:
        traced_figures.append(TracedFigure(
            format_paise_to_rupees(total_refunds), "total_refunds", total_refunds
        ))

    if "outstanding" in reconciliation:
        traced_figures.append(TracedFigure(
            format_paise_to_rupees(outstanding), "outstanding", outstanding
        ))

    if "peak_business_hour" in analytics:
        traced_figures.append(TracedFigure(
            f"{peak_hour}:00", "peak_business_hour", peak_hour
        ))

    return LLMStructuredResponse(narrative, traced_figures, source="fallback")


def generate_llm_narrative(deterministic_report: Dict[str, Any]) -> LLMStructuredResponse:
    """
    Generate a clinic-owner-facing narrative using LLM.
    Falls back to template-based narrative if LLM is not available or fails.
    """
    # Check if LLM is configured
    if not is_llm_configured():
        logger.info("LLM not configured, using fallback narrative")
        return create_fallback_narrative(deterministic_report)

    try:
        # Import Gemini client (lazy import to avoid hard dependency)
        try:
            import google.generativeai as genai
        except ImportError:
            logger.warning("Google Generative AI package not installed, using fallback narrative")
            return create_fallback_narrative(deterministic_report)

        config = get_llm_config()

        # Configure the Gemini API
        genai.configure(api_key=config.api_key)

        # Prepare the deterministic report summary for the LLM
        reconciliation = deterministic_report.get("reconciliation", {})
        analytics = deterministic_report.get("analytics", {})

        # Create a concise summary of the report
        report_summary = {
            "reconciliation": {
                "total_billed": reconciliation.get("total_billed", 0),
                "total_collected": reconciliation.get("total_collected", 0),
                "total_refunds": reconciliation.get("total_refunds", 0),
                "outstanding": reconciliation.get("outstanding", 0),
                "total_billed_by_mode": reconciliation.get("total_billed_by_mode", {}),
                "total_collected_by_mode": reconciliation.get("total_collected_by_mode", {}),
                "total_refunds_by_mode": reconciliation.get("total_refunds_by_mode", {}),
            },
            "analytics": {
                "peak_business_hour": analytics.get("peak_business_hour", 0),
                "revenue_by_hour": analytics.get("revenue_by_hour", {}),
                "top_medicines_by_quantity": analytics.get("top_medicines_by_quantity", [])[:3],  # Top 3
                "top_medicines_by_revenue": analytics.get("top_medicines_by_revenue", [])[:3],   # Top 3
            }
        }

        # Create the prompt
        prompt = f"""You are a helpful assistant that generates a concise, clinic-owner-facing summary of daily financial performance for WhatsApp communication.

Based on the deterministic report below, generate:
1. A short narrative in the exact format shown below (including the greeting, date, and all metrics). Do not add extra sentences or change the structure.
2. Traced figures for key metrics that must be pulled directly from the report.

Deterministic Report:
{json.dumps(report_summary, indent=2)}

Required narrative format (use this exact template, filling in the placeholders with the appropriate values from the report):
Good evening! Here's today's summary for Mehta Clinic ({date_str}):

₹{total_billed_rs} billed across {visit_count} visits, ₹{total_collected_rs} collected ({collection_pct}%).
₹{outstanding_rs} is still outstanding across {outstanding_visit_count} visits, and ₹{total_refunds_rs} was refunded on {refund_visit_count} visit(s).

Busiest hour: {peak_hour_str}-{next_hour_str}, with ₹{peak_revenue_rs} in revenue.

Top mover by quantity: {top_med_qty_name} ({top_med_qty} units).
Top by revenue: {top_med_rev_name} (₹{top_med_rev_rs}).

Note: cost data wasn't available today, so this is revenue, not profit - flagging rather than estimating.

Where:
- date_str: the date in the format "DD MMM" (e.g., "27 Jul") derived from the report's data (you can approximate using the peak_business_hour or any timestamp; if unavailable, use the date from the first record or assume today's date).
- total_billed_rs: total_billed converted to rupees with two decimal places (e.g., 42850).
- total_collected_rs: total_collected converted to rupees with two decimal places.
- collection_pct: integer percentage of total_collected / total_billed * 100 (if total_billed > 0) else 0.
- outstanding_rs: outstanding converted to rupees with two decimal places.
- outstanding_visit_count: number of visits with outstanding amount > 0 (you can approximate as the number of visits where amount_paid_paise < (visit_charge - discount_paise); if unable, set to 0).
- total_refunds_rs: total_refunds converted to rupees with two decimal places.
- refund_visit_count: number of refund visits (is_refund == true).
- peak_hour_str: peak_business_hour as integer (0-23).
- next_hour_str: (peak_business_hour + 1) % 24, formatted as two-digit hour? Actually format as "12pm-1pm" etc. We'll approximate: if peak_business_hour is 12, then "12pm-1pm"; if 23, then "11pm-12am". For simplicity, we can just output the hour range as "{peak_business_hour}:00-{peak_business_hour+1}:00" but the user example uses "12pm-1pm". We'll do our best.
- peak_revenue_rs: revenue in the peak hour (from revenue_by_hour[peak_business_hour]) converted to rupees.
- top_med_qty_name: drug name of the medicine with highest quantity (from top_medicines_by_quantity[0].drug_name).
- top_med_qty: quantity (integer).
- top_med_rev_name: drug name of the medicine with highest revenue (from top_medicines_by_revenue[0].drug_name).
- top_med_rev_rs: revenue_paise of that medicine converted to rupees.

If any of these values cannot be determined from the report, make a reasonable approximation or set to 0 / N/A, but keep the format exactly.

Requirements:
- Narrative must be in plain text, suitable for WhatsApp (no markdown)
- For traced figures, you MUST only use values that exist in the deterministic report
- Each traced figure must specify: display_value (formatted for display), report_field (the exact field name from report), and value (the raw value)
- Do not calculate or infer any values not present in the report
- If a metric cannot be determined from the report (e.g., profit without cost data), do not include it

Return ONLY a JSON object with this exact structure:
{{
  "narrative": "Your narrative text here (must follow the format above)",
  "traced_figures": [
    {{
      "display_value": "Formatted value for display (e.g., '₹1,234.56')",
      "report_field": "Exact field name from the report (e.g., 'total_billed')",
      "value": raw_value_from_report
    }}
  ]
}}

Key fields available in the report:
- total_billed (int, paise)
- total_collected (int, paise)
- total_refunds (int, paise)
- outstanding (int, paise)
- peak_business_hour (int, 0-23)
- total_billed_by_mode (dict with cash/card/upi keys)
- total_collected_by_mode (dict with cash/card/upi keys)
- total_refunds_by_mode (dict with cash/card/upi keys)
- visit_count (int) - we added this to deterministic_report
- refund_visit_count (int) - we added this
- revenue_by_hour (dict hour->int paise)
- top_medicines_by_quantity (list of {{drug_name: str, quantity: int}})
- top_medicines_by_revenue (list of {{drug_name: str, revenue_paise: int}})

Do not include any other fields in your response."""

        # Set up the model
        model = genai.GenerativeModel(config.model)

        # Generate content
        response = model.generate_content(prompt)

        # Extract the response text
        response_text = response.text.strip()

        # Try to parse JSON from the response
        try:
            # Find JSON in the response (handle potential extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON object found in response")

            json_str = response_text[json_start:json_end]
            llm_response = json.loads(json_str)

            # Validate and extract traced figures
            narrative, traced_figures, errors = validate_and_extract_traced_figures(
                llm_response,
                {**reconciliation, **analytics}  # Combine for validation
            )

            if errors:
                logger.warning(f"LLM response validation failed: {errors}")
                logger.info("Falling back to template narrative")
                return create_fallback_narrative(deterministic_report)

            return LLMStructuredResponse(narrative, traced_figures, source="llm")

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            logger.info("Falling back to template narrative")
            return create_fallback_narrative(deterministic_report)

    except Exception as e:
        logger.error(f"Error generating LLM narrative: {e}")
        logger.info("Falling back to template narrative")
        return create_fallback_narrative(deterministic_report)