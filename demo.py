"""Scripted end-to-end session for Kimi-EOS."""
from keos_pkg import Engine

SCRIPT = [
    ("personal",    None,        "took a loan of 50000 KES from KCB"),
    ("personal",    None,        "received 8000 KES from TRM guest for bnb stay to mpesa"),
    ("agribusiness",None,        "received 500 SCR from guest for taxi to sc bank"),
    ("agribusiness",None,        "spent 3500 KES on fuel from mpesa"),
    ("agribusiness",None,        "bought a water pump for 18000 KES from mpesa"),
    ("personal",    None,        "transferred 10000 KES from mpesa to bank"),
    ("personal",    None,        "paid 5000 KES loan to KCB from mpesa"),
    ("personal",    None,        "paid 60000 KES loan to KCB"),
    ("personal",    None,        "transferred 90000 KES from mpesa to bank"),
    ("personal",    "dup-key-1", "received 3000 KES from Mary for eggs"),
    ("personal",    "dup-key-1", "received 3000 KES from Mary for eggs"),
    ("personal",    None,        "the weather in Voi is lovely today"),
]

def main():
    eng = Engine()
    out = []
    for biz, key, text in SCRIPT:
        ok, msg = eng.process(text, business=biz, idem_key=key)
        line = f"> [{biz}] {text}\n  {msg}"
        print(line); out.append(line)
    print("\n" + eng.report())
    with open("/mnt/agents/output/keos/demo_transcript.txt", "w") as f:
        f.write("\n".join(out) + "\n\n" + eng.report() + "\n")

if __name__ == "__main__":
    main()
