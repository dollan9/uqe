"""Geometry helpers shared by vision, subtitles and QA modules.

All boxes are normalized (0..1) ``x0,y0,x1,y1`` unless stated otherwise.
"""

from __future__ import annotations

Box = tuple[float, float, float, float]


def box_area(b: Box) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def box_intersection(a: Box, b: Box) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def box_iou(a: Box, b: Box) -> float:
    inter = box_intersection(a, b)
    union = box_area(a) + box_area(b) - inter
    return inter / union if union > 1e-9 else 0.0


def box_overlap_ratio_over_b(a: Box, b: Box) -> float:
    """Fraction of box ``b`` covered by box ``a`` (asymmetric IoU)."""
    inter = box_intersection(a, b)
    area_b = box_area(b)
    return inter / area_b if area_b > 1e-9 else 0.0


def point_in_box(x: float, y: float, b: Box) -> bool:
    return b[0] <= x <= b[2] and b[1] <= y <= b[3]


def circle_box_overlap(cx: float, cy: float, r: float, b: Box) -> float:
    """Approximate fraction of a circle's area covered by an axis box."""
    # Clamp circle center into the box; measure distance to estimate overlap.
    nx = min(max(cx, b[0]), b[2])
    ny = min(max(cy, b[1]), b[3])
    d = ((nx - cx) ** 2 + (ny - cy) ** 2) ** 0.5
    if d >= r:
        return 0.0
    if d <= 0.0 and point_in_box(cx, cy, b):
        return 1.0
    # Circular-segment approximation for partial overlap.
    area = 3.141592653589793 * r * r
    seg = area * (1.0 - d / r) ** 1.5
    return min(1.0, seg / area) if area > 0 else 0.0


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t, 0.0, 1.0)


def denormalize_box(b: Box, width: int, height: int) -> tuple[int, int, int, int]:
    return (int(b[0] * width), int(b[1] * height), int(b[2] * width), int(b[3] * height))


def normalize_box(x0: float, y0: float, x1: float, y1: float, width: int, height: int) -> Box:
    w, h = max(width, 1), max(height, 1)
    return (clamp(x0 / w, 0, 1), clamp(y0 / h, 0, 1), clamp(x1 / w, 0, 1), clamp(y1 / h, 0, 1))


def box_center(b: Box) -> tuple[float, float]:
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def distance_xy(x0: float, y0: float, x1: float, y1: float) -> float:
    return ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
