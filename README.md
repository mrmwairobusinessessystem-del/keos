# Kimi-EOS — my independent re-implementation of the EOS concept

A clean-room version of EOS (Enterprise/Capital Operating System), built from the
handoff document's *architecture and doctrine*, not from its code. It honors the
same supreme rule:

> **Interface != Intelligence != Rules != Database.**
> AI proposes; the rules dispose; the database is the only truth.

## What this is

A complete, runnable, tested financial runtime that accepts natural-language
instructions and posts them as validated, double-entry, multi-currency,
audit-hashed transactions. It is what the original EOS runtime aims to be at its
core — provable end-to-end in one process, with no external services.

## Architecture

```
natural language text
      |
      v
+-------------------+   proposes a structured Event (NO authority)
|  EXTRACTOR        |   default: deterministic local parser (keos_pkg/parser.py)
|  (the "AI" slot)  |   swap: any callable(text) -> dict, e.g. Gemini/ChatGPT
+-------------------+
      |
      v
+-------------------+   THE AUTHORITY — validates & decides
|  RULES ENGINE     |   keos_pkg/rules.py
|                   |   - schema checks, known accounts/businesses/currencies
|                   |   - sufficient funds, outstanding-loan caps, distinct legs
|                   |   - idempotency (no double posting)
+-------------------+
      | any violation -> rejection audited, NOTHING touches the ledger
      v
+-------------------+   source of truth — SQLite
|  DOUBLE-ENTRY     |   - balanced postings (sum to zero in base currency)
|  LEDGER + AUDIT   |   - multi-currency: original amount/currency + rate + base
|                   |   - append-only, hash-chained audit log (tamper-evident)
+-------------------+
```

## Design decisions inherited from the handoff

- **"loan paid to bank/mpesa/person" = OUTGOING repayment** when the user is
  the payer (the handoff's explicit interpretation rule) — tested.
- **AI is not the financial authority.** The parser is replaceable; the rules
  are not. A rejected instruction changes nothing (atomicity tested).
- **Multi-currency retention:** original amount, original currency, rate, and
  base equivalent are all stored; the original is never overwritten (tested).
- **Idempotency:** transport glitches cannot double-post (tested).
- **Auditability:** every post *and every rejection* is written to a SHA-256
  hash chain (integrity tested).
- **Businesses:** `personal`, `agribusiness` (Taita Taveta), `trm` (TRM Drive BnB).

## How the real deployment would attach

This runtime is deliberately interface-agnostic. Production wiring per the
handoff's target path:

```
Telegram --webhook--> Make.com --HTTP--> keos Engine.process(text, idem_key=telegram_update_id)
                                              |
                                              v
                                    Supabase (swap SQLite store for Postgres,
                                    same entry/audit schema)
```

The idempotency key exists precisely because Make/Telegram can redeliver.

## Run it

```bash
cd keos
python demo.py                 # scripted end-to-end session (incl. deliberate failures)
python -m keos_pkg.cli         # interactive shell (:balances, :ledger, :biz <name>)
python -m pytest tests/ -q     # 18 tests
```

## Honest limits

- The extractor is deterministic regex — robust for the covered grammar, and a
  deliberate stand-in for an AI provider. In production it sits behind the same
  Event schema, so the rules engine is unchanged no matter how sloppy the AI is.
- One liability pool per lender, simple income/expense categories, no
  scheduling/alerts/RBAC yet — all listed as possible in handoff section 23.
