"""Webhook adapter: the TRANSPORT layer between interfaces and the EOS runtime."""
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from .engine import Engine
from .store import Store

STORE_PATH = os.environ.get("KEOS_DB", "eos.db")
_engine = Engine(store=Store(STORE_PATH))

def handle_update(payload: dict) -> dict:
    if "update_id" in payload and "message" in payload:
        msg = payload["message"]
        text = (msg.get("text") or "").strip()
        chat_id = msg["chat"]["id"]
        idem = f"tg:{payload['update_id']}"
        business = (msg.get("from", {}).get("username") or "personal")
        ok, reply = _engine.process(text, business=business, idem_key=idem)
        return {"ok": ok, "chat_id": chat_id, "reply": reply,
                "method": "sendMessage"}
    if "text" in payload:
        idem = payload.get("idem_key") or f"mk:{payload.get('message_id', '')}"
        ok, reply = _engine.process(payload["text"],
                                    business=payload.get("business", "personal"),
                                    idem_key=idem)
        return {"ok": ok, "reply": reply}
    return {"ok": False, "reply": "Unsupported payload shape."}

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") not in ("/webhook", "/telegram", "/make"):
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            payload = {"text": raw.decode("utf-8", "replace")}
        result = handle_update(payload)
        body = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            body = json.dumps({"status": "ok",
                               "audit_chain": _engine.store.audit_chain_ok()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *args):
        pass

def run(port=int(os.environ.get("PORT", "8080"))):
    print(f"keos adapter listening on :{port}  (POST /webhook, GET /health)")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

if __name__ == "__main__":
    run()
