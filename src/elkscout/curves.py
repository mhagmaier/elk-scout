"""Piecewise-linear suitability curves and aspect preference math.

A curve is a list of [x, y] breakpoints with strictly increasing x.
Outside the breakpoint range the curve clamps to the end values.
"""

from __future__ import annotations

import numpy as np

Curve = list[tuple[float, float]] | list[list[float]]


def validate_curve(points: Curve) -> list[tuple[float, float]]:
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 2:
        raise ValueError(f"curve needs >=2 points, got {pts}")
    xs = [p[0] for p in pts]
    if any(b <= a for a, b in zip(xs, xs[1:])):
        raise ValueError(f"curve x values must be strictly increasing: {xs}")
    for _, y in pts:
        if not (0.0 <= y <= 1.0):
            raise ValueError(f"curve y values must be within [0,1]: {pts}")
    return pts


def apply_curve(values: np.ndarray | float, points: Curve) -> np.ndarray:
    """Evaluate a piecewise-linear curve; clamps outside the range; NaN passes through."""
    pts = validate_curve(points)
    xs = np.array([p[0] for p in pts], dtype=np.float64)
    ys = np.array([p[1] for p in pts], dtype=np.float64)
    arr = np.asarray(values, dtype=np.float32)
    out = np.interp(arr, xs, ys).astype(np.float32)
    out = np.where(np.isnan(arr), np.nan, out)
    return out


def shift_curve_x(points: Curve, dx: float) -> list[tuple[float, float]]:
    """Shift every breakpoint's x by dx (e.g. snow pushing the elevation band down)."""
    return [(float(x) + dx, float(y)) for x, y in validate_curve(points)]


def aspect_score(aspect_deg: np.ndarray, center_deg: float, exponent: float = 1.0) -> np.ndarray:
    """Aspect preference in [0,1]: 1 facing `center_deg`, 0 facing opposite.

    score = (0.5 * (1 + cos(aspect - center)))**exponent, NaN-preserving.
    Flat cells (aspect NaN) should be handled by the caller (typically neutral 0.5).
    """
    a = np.asarray(aspect_deg, dtype=np.float32)
    rad = np.deg2rad(a - center_deg)
    base = 0.5 * (1.0 + np.cos(rad))
    out = np.power(base, exponent, dtype=np.float32)
    return np.where(np.isnan(a), np.nan, out).astype(np.float32)
