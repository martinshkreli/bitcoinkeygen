# Bitcoin Key‑Utility (`bitcoin_keygen.py`)

A compact, dependency‑light tool for

* deriving compressed public keys, WIF, and legacy/SegWit addresses  
  from decimal **private‑keys**  
* scanning a **range** of private‑keys in parallel and saving the results  
  to CSV  
* converting an existing **33‑byte compressed public key** to all three
  standard Bitcoin‑mainnet address formats (1… / 3… / bc1…)

The elliptic‑curve arithmetic is implemented from scratch (`secp256k1`)
for educational clarity—no external C libraries required.

---

## 1  Installation

```bash
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
