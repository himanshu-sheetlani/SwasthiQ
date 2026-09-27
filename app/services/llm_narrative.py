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
    def __init__(self, narrative: str, traced_figures: List[TracedFigure]):
        self.narrative = narrative
        self.traced_figures = traced_figures

    def to_dict(self) -> Dict[str, Any]:
        return {
            "narrative": self.narrative,
            "traced_figures": [figure.to_dict() for figure in self.traced_figures]
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


def create_fallback_narrative(deterministic_report: Dict[str, Any]) -> LLMStructuredResponse:
    """Create a fallback narrative when LLM is not available or fails."""
    reconciliation = deterministic_report.get("reconciliation", {})
    analytics = deterministic_report.get("analytics", {})

    # Extract key metrics
    total_billed = reconciliation.get("total_billed", 0)
    total_collected = reconciliation.get("total_collected", 0)
    total_refunds = reconciliation.get("total_refunds", 0)
    outstanding = reconciliation.get("outstanding", 0)
    peak_hour = analytics.get("peak_business_hour", 0)

    # Format for display
    total_billed_str = format_paise_to_rupees(total_billed)
    total_collected_str = format_paise_to_rupees(total_collected)
    total_refunds_str = format_paise_to_rupees(total_refunds)
    outstanding_str = format_paise_to_rupees(outstanding)
    peak_hour_str = f"{peak_hour}:00" if peak_hour > 0 else "No data"

    # Build narrative
    if total_refunds > 0 and total_billed == 0 and total_collected == 0:
        narrative = f"On the selected date, the clinic processed only refunds totaling {total_refunds_str}. No new bills were generated."
    elif total_billed == 0:
        narrative = f"On the selected date, there were no billing activities recorded."
    else:
        narrative = f"On the selected date, the clinic billed {total_billed_str}, collected {total_collected_str}"
        if total_refunds > 0:
            narrative += f", and processed refunds of {total_refunds_str}"
        narrative += f". The outstanding amount is {outstanding_str}"
        if peak_hour_str != "No data":
            narrative += f". Peak business hour was {peak_hour_str}."

    # Create traced figures
    traced_figures = []

    # Add traced figures for key metrics
    if "total_billed" in reconciliation:
        traced_figures.append(TracedFigure(
            total_billed_str, "total_billed", total_billed
        ))

    if "total_collected" in reconciliation:
        traced_figures.append(TracedFigure(
            total_collected_str, "total_collected", total_collected
        ))

    if "total_refunds" in reconciliation:
        traced_figures.append(TracedFigure(
            total_refunds_str, "total_refunds", total_refunds
        ))

    if "outstanding" in reconciliation:
        traced_figures.append(TracedFigure(
            outstanding_str, "outstanding", outstanding
        ))

    if "peak_business_hour" in analytics:
        traced_figures.append(TracedFigure(
            peak_hour_str, "peak_business_hour", peak_hour
        ))

    return LLMStructuredResponse(narrative, traced_figures)


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
        prompt = f"""You are a helpful assistant that generates concise, clinic-owner-facing summaries of daily financial performance for WhatsApp communication.

Based on the deterministic report below, generate:
1. A short narrative (2-3 sentences) suitable for WhatsApp that summarizes the day's financial performance
2. Traced figures for key metrics that must be pulled directly from the report

Deterministic Report:
{json.dumps(report_summary, indent=2)}

Requirements:
- Narrative must be in plain text, suitable for WhatsApp (no markdown)
- Include information about: billed amount, collected amount, outstanding amount, refunds (if any), peak business hour
- If no billing activity, state that clearly
- For traced figures, you MUST only use values that exist in the deterministic report
- Each traced figure must specify: display_value (formatted for display), report_field (the exact field name from report), and value (the raw value)
- Do not calculate or infer any values not present in the report
- If a metric cannot be determined from the report (e.g., profit without cost data), do not include it

Return ONLY a JSON object with this exact structure:
{{
  "narrative": "Your narrative text here",
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

            return LLMStructuredResponse(narrative, traced_figures)

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            logger.info("Falling back to template narrative")
            return create_fallback_narrative(deterministic_report)

    except Exception as e:
        logger.error(f"Error generating LLM narrative: {e}")
        logger.info("Falling back to template narrative")
        return create_fallback_narrative(deterministic_report)