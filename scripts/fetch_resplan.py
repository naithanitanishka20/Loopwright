"""Download ResPlan.zip (about 100 MB, CC BY 4.0) into data/.

Usage: python scripts/fetch_resplan.py
"""
import pathlib
import urllib.request

URL = "https://raw.githubusercontent.com/m-agour/ResPlan/main/ResPlan.zip"
dest = pathlib.Path(__file__).resolve().parent.parent / "data" / "ResPlan.zip"
dest.parent.mkdir(exist_ok=True)
if dest.exists():
    print(f"already there: {dest}")
else:
    print(f"downloading {URL}")
    urllib.request.urlretrieve(URL, dest)
    print(f"saved {dest} ({dest.stat().st_size:,} bytes)")
