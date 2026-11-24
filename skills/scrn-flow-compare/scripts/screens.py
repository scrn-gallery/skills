"""Shared helpers: download SCRN screens from the public CDN and cache them.

A screen reference is either a SCRN image id (24-hex string, the `preview`
or `original` field of a `get-flow` -> `screens_full` item) or a local file path.
"""
import os
import sys
import urllib.request
import concurrent.futures as cf
from PIL import Image

CDN = "https://scrn.gallery/cdn/{}.jpg"
CACHE = os.environ.get("SCRN_CACHE", os.path.join(os.getcwd(), ".scrn_cache"))


def _path_for(ref):
    if os.path.exists(ref):
        return ref
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, f"{ref}.img")


def fetch(ref):
    """Return a local path for a screen ref, downloading it if needed (None on failure)."""
    p = _path_for(ref)
    if os.path.exists(p) and os.path.getsize(p) > 0:
        return p
    try:
        req = urllib.request.Request(CDN.format(ref), headers={"User-Agent": "scrn-flow-compare"})
        with urllib.request.urlopen(req, timeout=30) as r, open(p, "wb") as f:
            f.write(r.read())
        return p
    except Exception as e:  # network blocked, 404, ...
        print(f"[screens] cannot fetch {ref}: {e}", file=sys.stderr)
        return None


def fetch_many(refs, workers=16):
    with cf.ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fetch, refs))


def load(ref):
    p = fetch(ref)
    if not p:
        return None
    try:
        return Image.open(p).convert("RGB")
    except Exception as e:
        print(f"[screens] cannot open {ref}: {e}", file=sys.stderr)
        return None


def check_cdn():
    """Quick connectivity check. Returns True if the CDN is reachable from this sandbox."""
    try:
        urllib.request.urlopen(urllib.request.Request("https://scrn.gallery/", headers={"User-Agent": "scrn-flow-compare"}), timeout=15)
        return True
    except Exception as e:
        print(f"[screens] scrn.gallery not reachable: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    print("CDN reachable:", check_cdn())
