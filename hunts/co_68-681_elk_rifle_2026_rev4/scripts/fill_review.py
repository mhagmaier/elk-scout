"""Fill data/work/imagery_review.json from a verdict file keyed by block id and
waypoint NAME (names are what the sheets show; the review file keys waypoints by
their stable wp_id).

verdicts.json: {"blocks": {"T01": "dense live conifer", ...},
                "waypoints": {"B3-01": "inside dense live conifer", ...}}
Waypoint keys may be the full name or its code (first token).

Usage (repo root): python3 fill_review.py --data data --verdicts <json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--verdicts", required=True)
    a = ap.parse_args()
    path = Path(a.data) / "work" / "imagery_review.json"
    review = json.loads(path.read_text())
    v = json.loads(Path(a.verdicts).read_text())
    missing = []
    for bid, entry in review["blocks"].items():
        if bid in v.get("blocks", {}):
            entry["verdict"] = v["blocks"][bid]
        else:
            missing.append(bid)
    by_code = {k.split()[0]: val for k, val in v.get("waypoints", {}).items()}
    for wid, entry in review["waypoints"].items():
        code = str(entry.get("name", "")).split()[0]
        if code in by_code:
            entry["verdict"] = by_code[code]
        else:
            missing.append(entry.get("name", wid))
    path.write_text(json.dumps(review, indent=1))
    filled_b = sum(1 for e in review["blocks"].values() if e.get("verdict"))
    filled_w = sum(1 for e in review["waypoints"].values() if e.get("verdict"))
    print(f"blocks {filled_b}/{len(review['blocks'])}, waypoints {filled_w}/{len(review['waypoints'])}; missing: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
