"""The EOS runtime: extraction -> validation -> rules -> posting -> audit."""
import hashlib, re, sqlite3, uuid
from . import parser, rules
from .models import Event, BASE_CURRENCY, norm_business
from .store import Store

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_") or "general"

class Engine:
    def __init__(self, store: Store = None, extractor=None):
        self.store = store or Store()
        self.extractor = extractor or parser.parse

    def process(self, text: str, business: str = "personal",
                idem_key: str = None):
        raw = self.extractor(text)
        ev = Event(**{k: v for k, v in raw.items() if k in Event.__dataclass_fields__})
        ev.business = business
        if idem_key is None:
            idem_key = hashlib.sha256(
                f"{norm_business(business) or business}|{text.lower().strip()}".encode()
            ).hexdigest()[:32]
        ev.idem_key = idem_key
        if ev.amount is not None and ev.currency:
            ev.rate = self.store.rate(ev.currency)
            ev.base_amount = round(ev.amount * ev.rate, 2) if ev.rate else None
        if ev.type == "LOAN_REPAYMENT" and (not ev.counterparty or ev.counterparty == "general"):
            outstanding = [r["name"] for r in self.store.conn.execute(
                "SELECT name FROM accounts WHERE kind='liability'")
                if self.store.balance(r["name"]) > 1e-9]
            if len(outstanding) == 1:
                ev.counterparty = outstanding[0].split(":", 1)[1]
        problems = rules.validate(self.store, ev)
        if problems:
            self.store.reject(ev.type, ev.business, text, problems)
            return False, "REJECTED — " + "; ".join(problems)
        entries = self._entries(ev)
        tx_id = uuid.uuid4().hex[:12]
        try:
            self.store.post(tx_id, idem_key, ev.type, ev.business, text, entries)
        except sqlite3.IntegrityError:
            self.store.reject(ev.type, ev.business, text, ["duplicate idempotency key"])
            return False, "REJECTED — duplicate event (already processed)."
        return True, self._reply(ev, tx_id)

    def _entries(self, ev: Event):
        a = ev.account; amt = ev.base_amount; orig = (ev.amount, ev.currency); E = []
        if ev.type == "INCOME":
            cat = "income:sales" if "sale" in (ev.description or "").lower() else "income:other"
            E = [(a, +amt, *orig, ev.description), (cat, +amt, None, None, ev.description)]
        elif ev.type == "EXPENSE":
            cat = "expense:" + ("fuel" if "fuel" in (ev.description or "").lower() else "general")
            E = [(cat, +amt, None, None, ev.description), (a, -amt, *orig, ev.description)]
        elif ev.type == "TRANSFER":
            E = [(ev.to_account, +amt, *orig, "transfer in"), (a, -amt, *orig, "transfer out")]
        elif ev.type == "LOAN_DISBURSEMENT":
            lender = "loans_payable:" + _slug(ev.counterparty)
            self.store.create_account(lender, "liability")
            E = [(a, +amt, *orig, f"loan from {ev.counterparty}"), (lender, +amt, None, None, f"owe {ev.counterparty}")]
        elif ev.type == "LOAN_REPAYMENT":
            lender = "loans_payable:" + _slug(ev.counterparty or "general")
            E = [(lender, -amt, None, None, f"repay {ev.counterparty}"), (a, -amt, *orig, f"loan repayment to {ev.counterparty}")]
        elif ev.type == "ASSET_PURCHASE":
            asset_acct = "assets:" + _slug(ev.asset)
            self.store.create_account(asset_acct, "asset")
            E = [(asset_acct, +amt, *orig, ev.asset), (a, -amt, *orig, f"purchase of {ev.asset}")]
        return E

    def _reply(self, ev: Event, tx_id: str) -> str:
        money = f"{ev.currency} {ev.amount:,.2f}"
        fx = f" (rate {ev.rate:g} -> {BASE_CURRENCY} {ev.base_amount:,.2f})" if ev.currency != BASE_CURRENCY else ""
        bal = self.store.balance(ev.account)
        if ev.type == "INCOME": body = f"income of {money}{fx} from {ev.counterparty or 'unknown'}"
        elif ev.type == "EXPENSE": body = f"expense of {money}{fx} for {ev.description or 'unspecified'}"
        elif ev.type == "TRANSFER": body = f"transfer of {money}{fx} {ev.account} -> {ev.to_account}"
        elif ev.type == "LOAN_DISBURSEMENT": body = f"loan of {money}{fx} received from {ev.counterparty}"
        elif ev.type == "LOAN_REPAYMENT": body = f"loan repayment of {money}{fx} to {ev.counterparty}"
        else: body = f"asset '{ev.asset}' acquired for {money}{fx}"
        return f"POSTED [{tx_id}] {body} (business: {ev.business}). {ev.account} balance: {BASE_CURRENCY} {bal:,.2f}."

    def report(self) -> str:
        lines = [f"BALANCES (base: {BASE_CURRENCY})", "-" * 44]
        for r in self.store.balances():
            if abs(r["b"]) > 1e-9 or r["kind"] == "asset":
                lines.append(f"{r['kind']:<10} {r['name']:<22} {r['b']:>12,.2f}")
        lines.append("-" * 44); lines.append(f"Audit chain intact: {self.store.audit_chain_ok()}")
        return "\n".join(lines)
