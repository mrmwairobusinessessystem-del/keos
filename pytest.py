"""Minimal pytest shim for environments without pytest installed.
Supports only what keos tests use: fixture, approx."""
class _Approx:
    def __init__(self, expected, rel=1e-6): self.expected=expected; self.rel=rel
    def __eq__(self, other): return abs(float(other)-float(self.expected)) <= self.rel*max(1.0,abs(float(self.expected)))
    def __repr__(self): return f"approx({self.expected})"
def approx(expected,rel=1e-6): return _Approx(expected,rel)
def fixture(func=None,**kwargs):
    def deco(f): return f
    return deco(func) if func else deco
