"""Read-only S3 listing/HEAD helper for Cell Painting Gallery.

Nothing here writes outside `data/external/`; it only asks S3 what exists and how big
it is, so a download budget can be planned *before* pulling anything.

    python scripts/s3_probe.py prefixes cpg0003-rosetta/broad/metadata/
    python scripts/s3_probe.py keys    cpg0003-rosetta/broad/metadata/ --max 40
    python scripts/s3_probe.py head    cpg0016-jump/source_1/workspace/load_data_csv/...
    python scripts/s3_probe.py glob    cpg0016-jump/source_1/workspace/load_data_csv/ --contains load_data.csv
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BUCKET = "cellpainting-gallery"
BASE = f"https://{BUCKET}.s3.amazonaws.com/"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def _get(query: str) -> ET.Element:
    req = urllib.request.Request(BASE + "?" + query,
                                 headers={"User-Agent": "Mozilla/5.0 (portfolio replication check)"})
    with urllib.request.urlopen(req, timeout=90) as fh:
        return ET.fromstring(fh.read())


def list_common_prefixes(prefix: str, marker: str = "") -> list:
    q = {"list-type": "2", "delimiter": "/", "prefix": prefix, "max-keys": "1000"}
    if marker:
        q["continuation-token"] = marker
    root = _get(urllib.parse.urlencode(q))
    return [c.find(NS + "Prefix").text for c in root.findall(NS + "CommonPrefixes")]


def list_keys(prefix: str, max_keys: int = 1000, marker: str = "") -> tuple:
    q = {"list-type": "2", "prefix": prefix, "max-keys": str(min(max_keys, 1000))}
    if marker:
        q["continuation-token"] = marker
    root = _get(urllib.parse.urlencode(q))
    out = []
    for c in root.findall(NS + "Contents"):
        out.append((c.find(NS + "Key").text, int(c.find(NS + "Size").text)))
    trunc = root.find(NS + "IsTruncated").text == "true"
    nxt = root.find(NS + "NextContinuationToken")
    return out, (nxt.text if nxt is not None else "") if trunc else "", trunc


def head(key: str) -> dict:
    req = urllib.request.Request(BASE + urllib.parse.quote(key),
                                 method="HEAD",
                                 headers={"User-Agent": "Mozilla/5.0 (portfolio replication check)"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        h = fh.headers
    return {"key": key, "size": int(h.get("Content-Length", -1)),
            "etag": (h.get("ETag") or "").strip('"'), "type": h.get("Content-Type"),
            "last_modified": h.get("Last-Modified")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["prefixes", "keys", "head", "glob"])
    ap.add_argument("prefix")
    ap.add_argument("--max", type=int, default=1000)
    ap.add_argument("--contains", default="")
    ap.add_argument("--pages", type=int, default=1, help="pages of 1000 keys to walk")
    a = ap.parse_args()

    if a.mode == "prefixes":
        print(json.dumps(list_common_prefixes(a.prefix), indent=1))
    elif a.mode == "head":
        print(json.dumps(head(a.prefix), indent=1))
    else:
        rows, pages = [], 0
        keys, marker, trunc = list_keys(a.prefix, a.max)
        while keys:
            for k, s in keys:
                if not a.contains or a.contains in k:
                    rows.append((k, s))
            pages += 1
            if not trunc or pages >= a.pages:
                break
            keys, marker, trunc = list_keys(a.prefix, 1000, marker)
        total = sum(s for _, s in rows)
        for k, s in rows[:200]:
            print(f"{s/1e6:9.2f} MB  {k}")
        print(f"\n{len(rows)} matched keys, total {total/1e6:.1f} MB "
              f"({total/1e9:.3f} GB)")
        if len(rows) > 200:
            print("(showing first 200)")


if __name__ == "__main__":
    sys.exit(main())
