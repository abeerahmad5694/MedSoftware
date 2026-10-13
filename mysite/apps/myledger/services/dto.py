from dataclasses import dataclass
from decimal import Decimal

@dataclass
class GledgLineDTO:
    accCode: int
    head: str
    notes: str
    receiptNo: int
    chqNo: str
    amount: Decimal
    refAccCode: int
    amtType: str = None
