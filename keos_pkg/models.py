from dataclasses import dataclass
from typing import Optional

BASE_CURRENCY = "KES"
EVENT_TYPES = ("INCOME", "EXPENSE", "TRANSFER", "LOAN_DISBURSEMENT", "LOAN_REPAYMENT", "ASSET_PURCHASE")
BUSINESSES = {"personal":"Personal Finances","agribusiness":"Taita Taveta Agribusiness","trm":"TRM Drive BnB"}
BUSINESS_ALIASES = {"taita":"agribusiness","taita taveta":"agribusiness","taita taveta agribusiness":"agribusiness","trm drive":"trm","trm drive bnb":"trm","bnb":"trm"}

def norm_business(name: str) -> str:
    key = " ".join((name or "").lower().strip().split())
    key = BUSINESS_ALIASES.get(key, key)
    return key if key in BUSINESSES else ""

@dataclass
class Event:
    type: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    account: Optional[str] = None
    to_account: Optional[str] = None
    counterparty: Optional[str] = None
    description: str = ""
    asset: Optional[str] = None
    business: str = "personal"
    idem_key: Optional[str] = None
    rate: Optional[float] = None
    base_amount: Optional[float] = None
