import sqlite3, json, hashlib
from datetime import datetime, timezone
from .models import BASE_CURRENCY

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts(
    name TEXT PRIMARY KEY, kind TEXT NOT NULL, currency TEXT NOT NULL DEFAULT 'KES');
CREATE TABLE IF NOT EXISTS rates(
    currency TEXT PRIMARY KEY, rate_to_base REAL NOT NULL, as_of TEXT);
CREATE TABLE IF NOT EXISTS transactions(
    id TEXT PRIMARY KEY, idem_key TEXT UNIQUE, type TEXT, business TEXT,
    description TEXT, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS entries(
    id INTEGER PRIMARY KEY AUTOINCREMENT, tx_id TEXT NOT NULL, account TEXT NOT NULL,
    signed_base REAL NOT NULL, original_amount REAL, original_currency TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS audit(
    seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, action TEXT,
    payload TEXT, prev_hash TEXT, hash TEXT);
"""

SEED_ACCOUNTS = [
    ("cash","asset","KES"),("mpesa","asset","KES"),("bank_kes","asset","KES"),("bank_scr","asset","SCR"),
    ("income:sales","income","KES"),("income:services","income","KES"),("income:other","income","KES"),
    ("expense:fuel","expense","KES"),("expense:food","expense","KES"),("expense:general","expense","KES"),
]
SEED_RATES = [("KES",1.0),("SCR",10.2),("USD",129.0),("EUR",140.5)]

class Store:
    def __init__(self, path=":memory:"):
        self.conn=sqlite3.connect(path,isolation_level=None); self.conn.row_factory=sqlite3.Row
        self.conn.executescript(SCHEMA); self._seed()
    def _seed(self):
        for name,kind,cur in SEED_ACCOUNTS: self.conn.execute("INSERT OR IGNORE INTO accounts(name,kind,currency) VALUES(?,?,?)",(name,kind,cur))
        for cur,rate in SEED_RATES: self.conn.execute("INSERT OR IGNORE INTO rates(currency,rate_to_base,as_of) VALUES(?,?,?)",(cur,rate,utcnow()))
        self.conn.commit()
        if self.conn.execute("SELECT COUNT(*) c FROM audit").fetchone()["c"]==0: self._audit("GENESIS",{"note":"store initialized","base":BASE_CURRENCY})
    def rate(self,currency):
        row=self.conn.execute("SELECT rate_to_base FROM rates WHERE currency=?",(currency,)).fetchone()
        return row["rate_to_base"] if row else None
    def account(self,name):
        return self.conn.execute("SELECT * FROM accounts WHERE name=?",(name,)).fetchone()
    def create_account(self,name,kind,currency=BASE_CURRENCY):
        self.conn.execute("INSERT OR IGNORE INTO accounts(name,kind,currency) VALUES(?,?,?)",(name,kind,currency))
    def balance(self,name):
        row=self.conn.execute("SELECT COALESCE(SUM(signed_base),0) b FROM entries WHERE account=?",(name,)).fetchone()
        return float(row["b"])
    def idem_seen(self,key):
        return self.conn.execute("SELECT 1 FROM transactions WHERE idem_key=?",(key,)).fetchone() is not None
    def balances(self):
        return self.conn.execute("""SELECT a.name,a.kind,a.currency,COALESCE(SUM(e.signed_base),0) b FROM accounts a LEFT JOIN entries e ON e.account=a.name GROUP BY a.name ORDER BY a.kind,a.name""").fetchall()
    def ledger(self,limit=50):
        return self.conn.execute("""SELECT t.created_at,t.type,t.business,t.description,e.account,e.signed_base,e.original_amount,e.original_currency FROM entries e JOIN transactions t ON t.id=e.tx_id WHERE t.status='POSTED' ORDER BY e.id DESC LIMIT ?""",(limit,)).fetchall()
    def post(self,tx_id,idem_key,type_,business,description,entries):
        try:
            self.conn.execute("BEGIN")
            self.conn.execute("INSERT INTO transactions VALUES(?,?,?,?,?,?,?)",(tx_id,idem_key,type_,business,description,"POSTED",utcnow()))
            for acct,signed,orig_amt,orig_cur,note in entries:
                self.conn.execute("INSERT INTO entries(tx_id,account,signed_base,original_amount,original_currency,note) VALUES(?,?,?,?,?,?)",(tx_id,acct,signed,orig_amt,orig_cur,note))
            self._audit("TX_POSTED",{"tx":tx_id,"type":type_,"business":business,"description":description}); self.conn.commit()
        except Exception: self.conn.rollback(); raise
    def reject(self,type_,business,description,problems):
        self._audit("TX_REJECTED",{"type":type_,"business":business,"description":description,"problems":problems}); self.conn.commit()
    def _audit(self,action,payload):
        prev=self.conn.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone(); prev_hash=prev["hash"] if prev else "0"*64
        body=json.dumps(payload,sort_keys=True,separators=(",",":")); h=hashlib.sha256((prev_hash+"|"+action+"|"+body).encode()).hexdigest()
        self.conn.execute("INSERT INTO audit(ts,action,payload,prev_hash,hash) VALUES(?,?,?,?,?)",(utcnow(),action,body,prev_hash,h))
    def audit_chain_ok(self):
        rows=self.conn.execute("SELECT * FROM audit ORDER BY seq").fetchall(); prev="0"*64
        for r in rows:
            if r["prev_hash"]!=prev: return False
            expect=hashlib.sha256((r["prev_hash"]+"|"+r["action"]+"|"+r["payload"]).encode()).hexdigest()
            if expect!=r["hash"]: return False
            prev=r["hash"]
        return True
