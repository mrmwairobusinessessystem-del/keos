"""Deterministic natural-language extraction."""
import re
CURRENCIES = ("KES", "SCR", "USD", "EUR")
ACCOUNT_ALIASES = {"mpesa":"mpesa","m-pesa":"mpesa","cash":"cash","bank":"bank_kes","kcb":"bank_kes","equity":"bank_kes","sc bank":"bank_scr","seychelles":"bank_scr"}
AMT = r"([d][d.,]*(?:\s*[kK](?![A-Za-z]))?)"
CUR = r"\s*([A-Za-z]{3}(?![A-Za-z]))?"

def _amount(tok: str) -> float:
    tok=tok.replace(",","").strip().lower(); mult=1000.0 if tok.endswith("k") else 1.0
    if tok.endswith("k"): tok=tok[:-1]
    return float(tok)*mult

def _currency(tok) -> str: return tok.upper() if tok else "KES"
def canon_account(tok: str):
    if not tok: return None
    return ACCOUNT_ALIASES.get(" ".join(tok.lower().strip().split()))
def _slug(s: str) -> str: return re.sub(r"[^a-z0-9]+","_",(s or "").lower()).strip("_") or "general"

def parse(text: str) -> dict:
    t=" ".join((text or "").strip().split())
    if not t: return {"type":"UNKNOWN"}
    low=t.lower()
    m=re.search(r"(?:transfer(?:red)?|moved)\s+"+AMT+CUR+r"\s+from\s+([a-z][\w .-]*?)\s+to\s+([a-z][\w .-]*?)$",t,re.I)
    if m:
        return {"type":"TRANSFER","amount":_amount(m.group(1)),"currency":_currency(m.group(2)),"account":canon_account(m.group(3)) or m.group(3).lower(),"to_account":canon_account(m.group(4)) or m.group(4).lower(),"description":t}
    m=re.search(r"(?:(?:took|got|received)\s+(?:a\s+)?loan\s+of|borrowed)\s+"+AMT+CUR+r"\s+from\s+(.+?)$",t,re.I)
    if m:
        lender=m.group(3).strip(); acct=None; mto=re.search(r"\s+to\s+([a-z][\w .-]*?)$",lender,re.I)
        if mto and canon_account(mto.group(1)): acct=canon_account(mto.group(1)); lender=lender[:mto.start()].strip()
        return {"type":"LOAN_DISBURSEMENT","amount":_amount(m.group(1)),"currency":_currency(m.group(2)),"counterparty":lender,"account":acct or "mpesa","description":t}
    acct=None; core=t
    mfrom=re.search(r"\s+from\s+([a-z][\w .-]*?)$",t,re.I)
    if mfrom and canon_account(mfrom.group(1)): acct=canon_account(mfrom.group(1)); core=t[:mfrom.start()]
    if "loan" in low and re.search(r"\b(paid|pay|repaid|repay)\b",low):
        m=re.search(AMT+CUR,core); target=""; m2=re.search(r"\bto\s+([a-z][\w .-]*?)$",core,re.I)
        if m2:
            target=m2.group(1).strip(); first=target.split()[0]
            if canon_account(first) and not acct:
                rest=" ".join(target.split()[1:]); acct=canon_account(first); target=rest if rest and not rest[0].isdigit() else ""
        return {"type":"LOAN_REPAYMENT","amount":_amount(m.group(1)) if m else None,"currency":_currency(m.group(2)) if m else "KES","counterparty":target if target else "general","account":acct or "mpesa","description":t}
    m=re.search(r"bought\s+(?:a\s+|an\s+)?(.+?)\s+for\s+"+AMT+CUR+r"(?:\s+from\s+(.+))?$",core,re.I)
    if m: return {"type":"ASSET_PURCHASE","asset":m.group(1).strip(),"amount":_amount(m.group(2)),"currency":_currency(m.group(3)),"counterparty":(m.group(4) or "").strip() or None,"account":acct or "mpesa","description":t}
    m=re.search(r"(?:received|got|earned)\s+"+AMT+CUR+r"(?:\s+from\s+(.+?))?(?:\s+for\s+(.+))?$",core,re.I)
    if m:
        dest=acct; mto=re.search(r"\s+to\s+([a-z][\w .-]*?)$",core,re.I)
        if mto and canon_account(mto.group(1)): dest=dest or canon_account(mto.group(1))
        return {"type":"INCOME","amount":_amount(m.group(1)),"currency":_currency(m.group(2)),"counterparty":(m.group(3) or "").strip() or None,"description":(m.group(4) or "").strip(),"account":dest or "mpesa"}
    m=re.search(r"(?:spent|paid)\s+"+AMT+CUR+r"\s+(?:on\s+(.+?)|to\s+(.+?))$",core,re.I)
    if m:
        desc=(m.group(3) or m.group(4) or "").strip()
        return {"type":"EXPENSE","amount":_amount(m.group(1)),"currency":_currency(m.group(2)),"account":acct or "mpesa","description":desc,"counterparty":desc}
    return {"type":"UNKNOWN","description":t}
