from typing import List, Dict, Tuple
from app.models.billing import BillingRecord
from collections import defaultdict

def compute_analytics(records: List[BillingRecord]) -> Dict:
    """
    Returns dict with:
    - revenue_by_hour: dict hour (0-23) -> net revenue in paise
    - peak_business_hour: int hour with max revenue
    - top_medicines_by_quantity: list of tuples (drug_name, quantity) sorted descending
    - top_medicines_by_revenue: list of tuples (drug_name, revenue_paise) sorted descending
    """
    # hourly revenue
    revenue_by_hour = defaultdict(int)  # hour -> net revenue paise
    # medicine aggregates
    med_qty = defaultdict(int)  # drug_name -> net quantity (positive for sale, negative for refund)
    med_rev = defaultdict(int)  # drug_name -> net revenue paise

    for r in records:
        # visit net amount after discount
        visit_charge = sum(item.qty * item.unit_price_paise for item in r.line_items)
        visit_net = visit_charge - r.discount_paise
        # net effect: if refund, negative
        net_effect = visit_net if not r.is_refund else -visit_net
        hour = r.timestamp.hour
        revenue_by_hour[hour] += net_effect

        # allocate net effect to each line item proportionally to line item charge
        line_item_charges = [item.qty * item.unit_price_paise for item in r.line_items]
        line_total = sum(line_item_charges)
        if line_total == 0:
            # avoid division by zero; allocate equally? but qty>0 and unit_price>0 so line_total>0
            continue
        for idx, item in enumerate(r.line_items):
            proportion = line_item_charges[idx] / line_total if line_total != 0 else 1 / len(r.line_items)
            allocated_net = net_effect * proportion
            # quantity contribution: signed qty
            signed_qty = item.qty if not r.is_refund else -item.qty
            med_qty[item.drug_name] += signed_qty
            # revenue contribution: allocated net (could be fractional paise; we need integer)
            # We'll round to nearest paise? Better to keep integer by using integer division with rounding.
            # We'll compute allocated net as integer using round.
            med_rev[item.drug_name] += int(round(allocated_net))

    # Determine peak hour
    peak_hour = max(revenue_by_hour.items(), key=lambda x: x[1], default=(0, 0))[0]

    # Sort medicines
    top_med_qty = sorted(med_qty.items(), key=lambda x: x[1], reverse=True)
    top_med_rev = sorted(med_rev.items(), key=lambda x: x[1], reverse=True)

    return {
        "revenue_by_hour": dict(revenue_by_hour),
        "peak_business_hour": peak_hour,
        "top_medicines_by_quantity": [{"drug_name": name, "quantity": qty} for name, qty in top_med_qty],
        "top_medicines_by_revenue": [{"drug_name": name, "revenue_paise": rev} for name, rev in top_med_rev],
    }
