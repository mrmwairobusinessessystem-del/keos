import sys
sys.path.insert(0, '.')
import tests.test_engine as T
from keos_pkg import Engine
results=[]
for name in sorted(dir(T)):
    if not name.startswith('test_'): continue
    fn=getattr(T,name)
    try:
        if fn.__code__.co_argcount==1: fn(Engine())
        else: fn()
        results.append((name,'PASS',''))
    except Exception as e: results.append((name,'FAIL',f'{type(e).__name__}: {e}'))
for name,status,err in results: print(f"{status}  {name}"+(f"  -> {err}" if err else ''))
print(f"\n{sum(1 for r in results if r[1]=='PASS')}/{len(results)} passed")
