"""ReferralHandshake (Protocol RHP-1) — 1-Command Scenario Seed & Reset Script.

Specification Anchors:
- Architecture §17: Demonstration Workflows & Proof Loops
- Solution §4.8: Scenarios S1-S6 Synthetic Seed Initializer
"""

import os
import sys
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def reset_and_seed():
    url = "http://localhost:8000/v1/demo/reset-and-seed"
    print(f"[*] Resetting and seeding synthetic demo scenarios via {url}...")
    try:
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[+] Status: {data.get('status', 'OK')} - {data.get('message', 'Seeded')}")
            return True
    except Exception as e:
        print(f"[-] Could not connect to running server at {url}: {e}")
        print("[*] Performing direct in-memory seed via api.rhp.db...")
        try:
            from api.rhp.db import GLOBAL_MOCK_DB
            GLOBAL_MOCK_DB.seed_defaults()
            print("[+] Direct in-memory reset and seed complete!")
            return True
        except Exception as inner_e:
            print(f"[!] Direct seed failed: {inner_e}")
            return False

if __name__ == "__main__":
    success = reset_and_seed()
    sys.exit(0 if success else 1)
