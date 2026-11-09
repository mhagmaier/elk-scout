"""Generate a hunt-ready ElkScout scoring profile from a species template.

    python scripts/gen_profile.py --species elk --weapon rifle --style backpack \
        --state ID --unit 33 --start 2026-10-10 --end 2026-10-17 [--days 5] \
        [--phase rut|general|late|high_country|transition|rut] \
        [--adjust factors.security.weight=0.3 ...] [--no-boundary] \
        --out configs/generated/id_33_elk_rifle.yaml

Deterministic: template -> phase deltas -> style overlay -> weapon overlay ->
user --adjust sets -> weight renormalization -> count rounding/clamping ->
elevation sanity clamp -> elkscout.config.load_config validation. Writes the
profile YAML plus a sibling .summary.md (weights table + biggest adjustments)
that the onx-scout skill shows the hunter before running the pipeline.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from elkscout.config import FACTOR_NAMES, Config  # noqa: E402
from elkscout.registry import load_states  # noqa: E402

TEMPLATES = {"elk": "elk.yaml", "mule_deer": "mule_deer.yaml"}
IDENTITY_PHASE = {"elk": "general", "mule_deer": "transition"}
ELEV_CLAMP_FT = (3000.0, 11500.0)


def _md(s: str) -> tuple[int, int]:
    m, d = s.split("-")
    return int(m), int(d)


def derive_phase(species: str, start: dt.date, adjustments: dict) -> tuple[str, str | None]:
    """(phase, warning) — phase from the species' date windows; identity if outside all."""
    start_md = (start.month, start.day)
    for phase, cell in adjustments["phases"][species].items():
        win = cell.get("window")
        if win and _md(win["start"]) <= start_md <= _md(win["end"]):
            return phase, None
    fallback = IDENTITY_PHASE[species]
    return fallback, (
        f"hunt start {start} is outside every defined {species} season window; "
        f"defaulting to the '{fallback}' (identity) phase — use --phase to override"
    )


def _set_path(doc: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    node = doc
    for k in keys[:-1]:
        nxt = node.get(k) if isinstance(node, dict) else None
        if not isinstance(nxt, dict):
            raise KeyError(f"path {dotted!r}: {k!r} not found in profile")
        node = nxt
    if keys[-1] not in node:
        raise KeyError(f"path {dotted!r}: {keys[-1]!r} not found in profile")
    node[keys[-1]] = value


def apply_cell(doc: dict, cell: dict, applied: list[str], layer: str) -> None:
    """Apply one matrix cell (phase/style/weapon) onto the profile dict."""
    if not cell:
        return
    for factor, mult in (cell.get("weights") or {}).items():
        if factor not in FACTOR_NAMES:
            raise KeyError(f"{layer}: unknown factor {factor!r} in weights")
        before = doc["factors"][factor]["weight"]
        doc["factors"][factor]["weight"] = before * float(mult)
        applied.append(f"{layer}: {factor} weight x{mult} ({before:.2f} -> {before * mult:.3f} pre-norm)")
    for curve_key, points in (cell.get("curves") or {}).items():
        factor, curve = curve_key.split(".", 1)
        if curve not in doc["factors"][factor]:
            raise KeyError(f"{layer}: factor {factor!r} has no curve {curve!r}")
        doc["factors"][factor][curve] = copy.deepcopy(points)
        applied.append(f"{layer}: replaced {curve_key}")
    for dotted, value in (cell.get("set") or {}).items():
        _set_path(doc, dotted, copy.deepcopy(value))
        applied.append(f"{layer}: set {dotted} = {value}")
    for wp_type, mult in (cell.get("counts") or {}).items():
        counts = doc["waypoints"]["counts"]
        if wp_type not in counts:
            raise KeyError(f"{layer}: waypoint type {wp_type!r} not in template counts")
        before = counts[wp_type]
        counts[wp_type] = 0 if float(mult) == 0 else max(1, round(before * float(mult)))
        applied.append(f"{layer}: {wp_type} count {before} -> {counts[wp_type]}")
    if cell.get("notes"):
        applied.append(f"{layer} doctrine: {cell['notes'].strip()}")


def finalize(doc: dict, applied: list[str]) -> None:
    # Renormalize factor weights to sum 1.0.
    total = sum(doc["factors"][f]["weight"] for f in FACTOR_NAMES)
    if total <= 0:
        raise ValueError("factor weights sum to zero after adjustments")
    for f in FACTOR_NAMES:
        doc["factors"][f]["weight"] = round(doc["factors"][f]["weight"] / total, 4)
    # Elevation-curve sanity clamp.
    curve = doc["factors"]["elevation"]["curve_elevation_ft"]
    lo, hi = ELEV_CLAMP_FT
    doc["factors"]["elevation"]["curve_elevation_ft"] = [
        [min(max(float(x), lo), hi), float(y)] for x, y in curve
    ]
    # Clamp total waypoint count to the GPX limit (defense in depth; writer re-checks).
    counts = doc["waypoints"]["counts"]
    limit = doc["outputs"]["gpx_max_waypoints"]
    if sum(counts.values()) > limit:
        scale = limit / sum(counts.values())
        for k in counts:
            counts[k] = max(1, int(counts[k] * scale))
        applied.append(f"clamped waypoint counts to GPX limit {limit}")


def summarize(doc: dict, applied: list[str], args, phase: str, warning: str | None) -> str:
    lines = [
        f"# Model summary — {doc['profile']}",
        "",
        f"**{args.species.replace('_', ' ')}**, {args.weapon}, {args.style} style — "
        f"unit {doc['unit']} ({args.state or 'no state'}), "
        f"{doc['hunt_window']['start']} to {doc['hunt_window']['end']}"
        + (f", {args.days} hunting days" if args.days else ""),
        "",
        f"Season phase: **{phase}**" + (f"  \n⚠ {warning}" if warning else ""),
        "",
        "| factor | weight |",
        "|---|---|",
    ]
    for f in FACTOR_NAMES:
        lines.append(f"| {f} | {doc['factors'][f]['weight']:.2f} |")
    lines += ["", "## Adjustments applied", ""]
    lines += [f"- {a}" for a in applied] if applied else ["- none — identity profile"]
    lines += [
        "",
        "_Generated by scripts/gen_profile.py; numeric source: configs/adjustments.yaml._",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--species", required=True, choices=sorted(TEMPLATES))
    ap.add_argument("--weapon", required=True, choices=["archery", "muzzleloader", "rifle"])
    ap.add_argument("--style", required=True, choices=["day", "backpack", "horseback"])
    ap.add_argument("--state", default=None, help="registry state code (e.g. ID); see configs/states.yaml")
    ap.add_argument("--unit", required=True)
    ap.add_argument("--start", required=True, type=dt.date.fromisoformat)
    ap.add_argument("--end", required=True, type=dt.date.fromisoformat)
    ap.add_argument("--phase", default=None, help="override the date-derived season phase")
    ap.add_argument("--days", type=int, default=None, help="hunting days (recorded for the guide)")
    ap.add_argument("--adjust", action="append", default=[], metavar="PATH=VALUE",
                    help="absolute set of a dotted config path, applied last (repeatable)")
    ap.add_argument("--no-boundary", action="store_true",
                    help="skip boundary injection (manual data/manual/boundary.geojson expected)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    with open(REPO / "configs" / "templates" / TEMPLATES[args.species], encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    with open(REPO / "configs" / "adjustments.yaml", encoding="utf-8") as fh:
        adjustments = yaml.safe_load(fh)

    phase, warning = (args.phase, None) if args.phase else derive_phase(args.species, args.start, adjustments)
    if phase not in adjustments["phases"][args.species]:
        ap.error(f"--phase {phase!r}: unknown for {args.species}; "
                 f"choose from {sorted(adjustments['phases'][args.species])}")

    applied: list[str] = []
    apply_cell(doc, adjustments["phases"][args.species][phase], applied, f"phase:{phase}")
    apply_cell(doc, adjustments["styles"][args.style], applied, f"style:{args.style}")
    apply_cell(doc, adjustments["weapons"][args.weapon], applied, f"weapon:{args.weapon}")

    doc["profile"] = f"{args.species}-{phase}-{args.weapon}-{args.style}"
    doc["unit"] = str(args.unit)
    doc["hunt_window"] = {"start": args.start, "end": args.end}

    if not args.no_boundary:
        if not args.state:
            ap.error("--state is required unless --no-boundary is given")
        states = load_states()
        code = args.state.upper()
        if code not in states:
            ap.error(
                f"state {code!r} is not in configs/states.yaml (have: {', '.join(sorted(states))}). "
                "Discover + register its boundary service "
                "(.claude/skills/onx-scout/references/state-discovery.md) or export the unit "
                "polygon to data/manual/boundary.geojson and re-run with --no-boundary."
            )
        entry = states[code]
        doc["boundary"] = entry.boundary.model_dump(mode="json")
        if entry.provenance.status != "verified":
            applied.append(f"NOTE: {code} boundary service is PROVISIONAL — verify before trusting")

    for item in args.adjust:
        if "=" not in item:
            ap.error(f"--adjust expects PATH=VALUE, got {item!r}")
        dotted, raw = item.split("=", 1)
        _set_path(doc, dotted.strip(), yaml.safe_load(raw))
        applied.append(f"user: set {dotted.strip()} = {raw}")

    finalize(doc, applied)
    cfg = Config.model_validate(doc)  # hard-fail before writing anything

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"# Generated by scripts/gen_profile.py — do not hand-edit curve numbers.\n"
        f"# {cfg.profile} | unit {cfg.unit} | {args.start} to {args.end}"
        + (f" | {args.days} days" if args.days else "") + "\n"
        + yaml.safe_dump(doc, sort_keys=False, default_flow_style=None, allow_unicode=False),
        encoding="utf-8",
    )
    summary_path = out.with_suffix(".summary.md")
    summary_path.write_text(summarize(doc, applied, args, phase, warning), encoding="utf-8")
    print(f"wrote {out}\nwrote {summary_path}")
    if warning:
        print(f"WARNING: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
