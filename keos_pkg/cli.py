import sys
from .engine import Engine

BANNER = """Kimi-EOS runtime — type natural-language financial instructions.
Commands:  :balances   :ledger   :quit
Businesses: personal (default), agribusiness, trm
Examples:  received 5000 KES from John for maize sales
           spent 1200 on fuel from mpesa
           took a loan of 50000 from KCB
           paid 5000 KES loan to KCB from mpesa
           transferred 2000 from mpesa to bank
           bought a water pump for 18000
"""

def main():
    eng = Engine()
    print(BANNER)
    while True:
        try:
            line = input("eos> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not line:
            continue
        if line in (":quit", ":exit"):
            break
        if line == ":balances":
            print(eng.report()); continue
        if line == ":ledger":
            for row in eng.store.ledger():
                print(dict(row))
            continue
        if line.startswith(":biz "):
            main._biz = line.split(None, 1)[1].strip()
            print(f"Business set to: {main._biz}"); continue
        ok, msg = eng.process(line, business=getattr(main, "_biz", "personal"))
        print(msg)

if __name__ == "__main__":
    sys.exit(main())
