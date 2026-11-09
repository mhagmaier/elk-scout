"""Build data/manual/snow.json for elkscout from NRCS AWDB (SNOTEL).

The pipeline's own station query sends bbox/network params that the AWDB v1
/stations endpoint ignores (it returns every station nationwide and the /data
call then fails with 414). This does the same job with params AWDB honors:
state-wildcard triplets, then a local bbox filter with the config's pad, then
the pipeline's own _summarize() so median + band shift use the profile curve.

Usage (repo root): python3 make_snow.py --config <profile.yaml> --data data
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

import requests  # noqa: E402

from elkscout import endpoints  # noqa: E402
from elkscout.config import load_config  # noqa: E402
from elkscout.grid import Grid  # noqa: E402
from elkscout.paths import Workspace  # noqa: E402
from elkscout.sources.snotel import _summarize  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--data", default="data")
    ap.add_argument("--state", default="CO")
    a = ap.parse_args()
    cfg = load_config(a.config)
    ws = Workspace(Path(a.data))
    minlon, minlat, maxlon, maxlat = Grid.load(ws.grid_json).bbox4326()
    pad = cfg.snow.station_bbox_pad_deg

    r = requests.get(
        f"{endpoints.AWDB}/stations",
        params={"stationTriplets": f"*:{a.state}:SNTL", "activeOnly": "true"},
        timeout=60,
    )
    r.raise_for_status()
    stations = [
        s for s in r.json()
        if s.get("latitude") is not None and s.get("longitude") is not None
        and minlat - pad <= s["latitude"] <= maxlat + pad
        and minlon - pad <= s["longitude"] <= maxlon + pad
    ]
    triplets = [s["stationTriplet"] for s in stations]
    print(f"{len(triplets)} SNOTEL station(s) in padded bbox: {[s['name'] for s in stations]}")

    today = dt.date.today()
    d = requests.get(
        f"{endpoints.AWDB}/data",
        params={
            "stationTriplets": ",".join(triplets),
            "elements": "SNWD,WTEQ",
            "duration": "DAILY",
            "beginDate": (today - dt.timedelta(days=7)).isoformat(),
            "endDate": today.isoformat(),
        },
        timeout=60,
    )
    d.raise_for_status()
    latest: dict[str, dict] = {t: {} for t in triplets}
    for entry in d.json():
        t = entry.get("stationTriplet")
        for el in entry.get("data") or []:
            code = ((el.get("stationElement") or {}).get("elementCode") or "").upper()
            vals = [v.get("value") for v in el.get("values") or [] if v.get("value") is not None]
            if t in latest and code in ("SNWD", "WTEQ") and vals:
                latest[t][code] = float(vals[-1])

    rows = [
        {
            "triplet": s["stationTriplet"],
            "name": s.get("name"),
            "elevation_ft": s.get("elevation"),
            "snwd_in": latest[s["stationTriplet"]].get("SNWD"),
            "wteq_in": latest[s["stationTriplet"]].get("WTEQ"),
        }
        for s in stations
    ]
    result = _summarize(rows, cfg)
    out = ws.manual_path("snow")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
