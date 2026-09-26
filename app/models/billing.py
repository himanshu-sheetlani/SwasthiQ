from pydantic import BaseModel, Field, validator, model_validator
from typing import List, Literal
from datetime import datetime

PaymentMode = Literal["cash", "card", "upi"]

class LineItem(BaseModel):
    drug_name: str = Field(..., min_length=1)
    qty: int = Field(..., gt=0)
    unit_price_paise: int = Field(..., gt=0)

    @validator('drug_name')
    def drug_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('drug_name must not be empty')
        return v.strip()

class BillingRecord(BaseModel):
    clinic_id: str = Field(..., min_length=1)
    visit_id: str = Field(..., min_length=1)
    timestamp: datetime
    doctor_id: str = Field(..., min_length=1)
    line_items: List[LineItem] = Field(..., min_items=1)
    payment_mode: PaymentMode
    amount_paid_paise: int
    discount_paise: int = Field(..., ge=0)
    is_refund: bool

    @validator('timestamp', pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            v = v.replace('Z', '+00:00')
            return datetime.fromisoformat(v)
        return v

    @validator('amount_paid_paise')
    def amount_paid_paise_int(cls, v):
        if not isinstance(v, int):
            raise ValueError('amount_paid_paise must be integer')
        return v

    @validator('discount_paise')
    def discount_paise_non_negative(cls, v):
        if v < 0:
            raise ValueError('discount_paise must be non-negative')
        return v

    @validator('clinic_id', 'visit_id', 'doctor_id')
    def id_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('field must not be empty')
        return v.strip()

    @model_validator(mode='after')
    def refund_amount_sign(self):
        if self.is_refund:
            if self.amount_paid_paise >= 0:
                raise ValueError('amount_paid_paise must be negative for refunds')
        else:
            if self.amount_paid_paise <= 0:
                raise ValueError('amount_paid_paise must be positive for non-refunds')
        return self
