import pytest
from keos_pkg import Engine
from keos_pkg.models import BASE_CURRENCY
@pytest.fixture
def eng(): return Engine()
def test_income_posts_and_updates_balance(eng):
    ok,msg=eng.process("received 5000 KES from John for maize sales"); assert ok,msg; assert eng.store.balance("mpesa")==5000; assert eng.store.balance("income:sales")==5000
def test_expense_reduces_balance(eng):
    eng.process("received 10000 from John"); ok,msg=eng.process("spent 1200 on fuel from mpesa"); assert ok,msg; assert eng.store.balance("mpesa")==8800; assert eng.store.balance("expense:fuel")==1200
def test_transfer_between_accounts(eng):
    eng.process("received 10000 from John"); ok,msg=eng.process("transferred 4000 from mpesa to bank"); assert ok,msg; assert eng.store.balance("mpesa")==6000; assert eng.store.balance("bank_kes")==4000
def test_transfer_same_account_rejected(eng):
    eng.process("received 10000 from John"); ok,msg=eng.process("transferred 4000 from mpesa to mpesa"); assert not ok and "differ" in msg
def test_loan_paid_to_bank_is_outgoing_repayment(eng):
    eng.process("took a loan of 50000 KES from KCB"); ok,msg=eng.process("paid 5000 KES loan to KCB from mpesa"); assert ok,msg; assert eng.store.balance("loans_payable:kcb")==45000; assert eng.store.balance("mpesa")==45000
def test_loan_paid_to_mpesa_keyword_form(eng):
    eng.process("took a loan of 20000 KES from Jane"); ok,msg=eng.process("loan paid to mpesa 3000 KES"); assert ok,msg; assert eng.store.balance("loans_payable:jane")==17000
def test_cannot_repay_more_than_outstanding(eng):
    eng.process("took a loan of 10000 from KCB"); ok,msg=eng.process("paid 12000 KES loan to KCB"); assert not ok and "exceeds outstanding" in msg
def test_repayment_unknown_lender_rejected(eng):
    eng.process("received 50000 from John"); ok,msg=eng.process("paid 3000 KES loan to Stranger"); assert not ok and "No outstanding loan" in msg
def test_insufficient_funds_rejected_atomically(eng):
    eng.process("received 5000 from John"); ok,msg=eng.process("transferred 9000 from mpesa to bank"); assert not ok and "Insufficient funds" in msg; assert eng.store.balance("mpesa")==5000
def test_unknown_account_rejected(eng):
    ok,msg=eng.process("received 5000 KES to saturn"); assert not ok and "interpret" in msg
def test_unknown_text_rejected_gracefully(eng):
    ok,msg=eng.process("hello there, how are you?"); assert not ok and "could not interpret" in msg
def test_duplicate_event_idempotent(eng):
    ok1,_=eng.process("received 5000 from John",idem_key="abc123"); ok2,msg2=eng.process("received 5000 from John",idem_key="abc123"); assert ok1 and not ok2; assert "duplicate" in msg2.lower(); assert eng.store.balance("mpesa")==5000
def test_multicurrency_retains_original_and_base(eng):
    eng.process("received 500 SCR from guest for taxi to sc bank"); assert eng.store.balance("bank_scr")==pytest.approx(500*10.2); row=eng.store.conn.execute("SELECT original_amount, original_currency FROM entries WHERE original_currency='SCR'").fetchone(); assert row["original_amount"]==500 and row["original_currency"]=="SCR"
def test_unknown_currency_rejected(eng):
    ok,msg=eng.process("received 500 JPY from guest"); assert not ok and "exchange rate" in msg
def test_audit_chain_intact_after_mixed_traffic(eng):
    eng.process("received 10000 from John"); eng.process("spent 1200 on fuel"); eng.process("transferred 90000 from mpesa to bank"); eng.process("paid 5000 KES loan to Ghost"); assert eng.store.audit_chain_ok()
def test_asset_purchase_creates_asset_account(eng):
    eng.process("received 50000 from John"); ok,msg=eng.process("bought a water pump for 18000 from agrovet"); assert ok,msg; assert eng.store.balance("assets:water_pump")==18000; assert eng.store.balance("mpesa")==32000
def test_business_dimension_recorded(eng):
    eng.process("received 8000 from TRM guest for bnb stay",business="trm"); rows=eng.store.conn.execute("SELECT business FROM transactions WHERE status='POSTED'").fetchall(); assert rows[0]["business"]=="trm"
