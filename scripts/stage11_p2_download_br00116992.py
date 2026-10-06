# -*- coding: utf-8 -*-
"""Stage 11 P2-A: download BR00116992 treated-well raw images (f01, 8 channels) from public S3."""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
OUT = os.path.join(BASE, "data", "raw", "BR00116992")
os.makedirs(OUT, exist_ok=True)

S3_PREFIX = ("https://cellpainting-gallery.s3.amazonaws.com/cpg0000-jump-pilot/source_4/images/"
             "2020_11_04_CPJUMP1/images/BR00116992__2020-11-05T21_31_31-Measurement1/Images/")

WELLS = ["A01","A03","A04","B12","O16","G05","J11","A21","O02","B02","L23",
         "A05","A06","A07","A08","A10","A11","A12"]

def well_to_site(w):
    row = ord(w[0]) - ord('A') + 1
    col = int(w[1:])
    return f"r{row:02d}c{col:02d}"

def url_for(site, ch):
    return f"{S3_PREFIX}{site}f01p01-ch{ch}sk1fk1fl1.tiff"

def download_one(item):
    site, ch, dest = item
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return site, ch, "exists", os.path.getsize(dest)
    try:
        req = Request(url_for(site, ch), headers={"User-Agent": "Mozilla/5.0"})
        t0 = time.time()
        with urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            data = r.read()
            f.write(data)
        return site, ch, "ok", len(data), round(time.time() - t0, 1)
    except Exception as e:
        return site, ch, f"FAIL:{type(e).__name__}:{str(e)[:120]}", 0

items = []
for w in WELLS:
    site = well_to_site(w)
    for ch in range(1, 9):
        dest = os.path.join(OUT, f"{site}f01p01-ch{ch}sk1fk1fl1.tiff")
        items.append((site, ch, dest))

print(f"total files to ensure: {len(items)} ({len(WELLS)} wells x 8 ch)", flush=True)
t0 = time.time()
results = []
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(download_one, it) for it in items]
    for fu in as_completed(futs):
        results.append(fu.result())

ok = [r for r in results if r[2] == "ok"]
exists = [r for r in results if r[2] == "exists"]
fails = [r for r in results if str(r[2]).startswith("FAIL")]
print(f"downloaded={len(ok)} exists={len(exists)} failed={len(fails)} elapsed={time.time()-t0:.1f}s", flush=True)
for r in fails[:20]:
    print("FAIL", r[0], r[2], flush=True)

# verify final inventory
import glob
tiffs = sorted(glob.glob(os.path.join(OUT, "*.tiff")))
sites = sorted({os.path.basename(p).split("-")[0] for p in tiffs})
print("final tiffs:", len(tiffs), "sites:", len(sites), flush=True)
sizes = [os.path.getsize(p) for p in tiffs]
print("size min/max/avg:", min(sizes), max(sizes), sum(sizes)//max(len(sizes),1), "total MB:", round(sum(sizes)/1e6, 1), flush=True)
if fails:
    sys.exit(2)
