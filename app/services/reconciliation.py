from typing import List, Dict
from app.models.billing import BillingRecord

def compute_reconciliation(records: List[BillingRecord]) -> Dict:
    """
    Returns a dict with:
    - total_billed: int (paise)
    - total_collected: int (paise)
    - total_refunds: int (paise, positive)
    - outstanding: int (paise)
    Each with payment_mode breakdown where applicable.
    """
    total_billed = 0
    total_collected = 0
    total_refunds = 0
    outstanding = 0

    # breakdowns
    billed_by_mode = {"cash": 0, "card": 0, "upi": 0}
    collected_by_mode = {"cash": 0, "card": 0, "upi": 0}
    refunds_by_mode = {"cash": 0, "card": 0, "upi": 0}

    for r in records:
        # compute visit total charge
        visit_charge = sum(item.qty * item.unit_price_paise for item in r.line_items)
        visit_net = visit_charge - r.discount_paise  # amount due after discount

        if r.is_refund:
            # refund: money out
            refund_amount = -r.amount_paid_paise  # should be positive
            total_refunds += refund_amount
            refunds_by_mode[r.payment_mode] += refund_amount
            # refunds do not affect billed or collected
        else:
            # normal visit
            total_billed += visit_net
            billed_by_mode[r.payment_mode] += visit_net

            total_collected += r.amount_paid_paise
            collected_by_mode[r.payment_mode] += r.amount_paid_paise

    outstanding = total_billed - total_collected

    return {
        "total_billed": total_billed,
        "total_billed_by_mode": billed_by_mode,
        "total_collected": total_collected,
        "total_collected_by_mode": collected_by_mode,
        "total_refunds": total_refunds,
        "total_refunds_by_mode": refunds_by_mode,
        "outstanding": outstanding,
        # outstanding breakdown? Not required but we can compute if needed
        # "outstanding_by_mode": {...}
    }
