"""The RULES are the authority."""
from .models import norm_business, EVENT_TYPES
def validate(store, ev) -> list:
    p=[]; add=p.append
    if ev.type=="UNKNOWN": add("I could not interpret that instruction. No money was moved."); return p
    if ev.type not in EVENT_TYPES: add(f"Unsupported event type: {ev.type}.")
    if ev.amount is None or ev.amount<=0: add("Amount is missing or not positive.")
    if not ev.currency: add("Currency is missing.")
    elif store.rate(ev.currency) is None: add(f"No exchange rate on record for {ev.currency}.")
    biz=norm_business(ev.business)
    if not biz: add(f"Unknown business '{ev.business}'. Known: personal, agribusiness, trm.")
    else: ev.business=biz
    if ev.idem_key and store.idem_seen(ev.idem_key): add("Duplicate event (already processed). Ignored to prevent double-posting.")
    def asset_ok(name,label):
        if not name: add(f"{label} account is missing."); return False
        row=store.account(name)
        if not row: add(f"Unknown {label} account '{name}'."); return False
        if row["kind"]!="asset": add(f"'{name}' is not an asset account."); return False
        return True
    def funds_ok(name):
        if ev.base_amount and store.balance(name)<ev.base_amount-1e-9: add(f"Insufficient funds in {name}: balance {store.balance(name):,.2f} < {ev.base_amount:,.2f} KES."); return False
        return True
    if ev.type=="INCOME": asset_ok(ev.account,"Destination")
    elif ev.type=="EXPENSE":
        if asset_ok(ev.account,"Source"): funds_ok(ev.account)
    elif ev.type=="TRANSFER":
        if not ev.to_account: add("Transfer destination is missing.")
        elif ev.to_account==ev.account: add("Source and destination must differ.")
        if asset_ok(ev.account,"Source") and asset_ok(ev.to_account,"Destination"): funds_ok(ev.account)
    elif ev.type=="LOAN_DISBURSEMENT":
        if not ev.counterparty: add("Lender is missing.")
        asset_ok(ev.account,"Destination")
    elif ev.type=="LOAN_REPAYMENT":
        if asset_ok(ev.account,"Source") and ev.base_amount:
            lender="loans_payable:"+_slug(ev.counterparty or "general"); outstanding=store.balance(lender)
            if outstanding<=0: add(f"No outstanding loan recorded for '{ev.counterparty}'.")
            elif outstanding<ev.base_amount-1e-9: add(f"Repayment exceeds outstanding loan for {ev.counterparty}: outstanding {outstanding:,.2f} KES.")
            funds_ok(ev.account)
    elif ev.type=="ASSET_PURCHASE":
        if not ev.asset: add("Asset description is missing.")
        if asset_ok(ev.account,"Source"): funds_ok(ev.account)
    return p
def _slug(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+","_",(s or "").lower()).strip("_") or "general"
