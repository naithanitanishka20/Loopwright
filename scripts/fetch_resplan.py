"""Download ResPlan.zip (about 100 MB, CC BY 4.0) and split.json into data/.

Usage: python scripts/fetch_resplan.py
"""
import pathlib
import urllib.request

BASE = "https://raw.githubusercontent.com/m-agour/ResPlan/main/"
data = pathlib.Path(__file__).resolve().parent.parent / "data"
data.mkdir(exist_ok=True)
for name in ("ResPlan.zip", "split.json"):
    dest = data / name
    if dest.exists():
        print(f"already there: {dest}")
        continue
    print(f"downloading {BASE + name}")
    urllib.request.urlretrieve(BASE + name, dest)
    print(f"saved {dest} ({dest.stat().st_size:,} bytes)")
