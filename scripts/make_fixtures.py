"""Generate the procedural fixture AOI as manual drop-in files.

Usage: python scripts/make_fixtures.py --out data/manual [--seed 42]
"""

import argparse
from pathlib import Path

from elkscout.testkit import make_fixtures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="output directory (a data/manual/-shaped dir)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    make_fixtures(Path(args.out), seed=args.seed)
    print(f"fixtures written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
