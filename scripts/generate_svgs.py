#!/usr/bin/env python3
"""
Generate scale-accurate technical SVG drawings for D-Sub connectors.

Output units are millimeters (mm).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

from report_catalog import build_catalog


Point = Tuple[float, float]


@dataclass(frozen=True)
class DSubSpec:
    label: str
    designation: str
    density: str
    file_tag: str
    pin_count: int
    rows: int
    row_counts: Optional[List[int]]
    row_offsets: Optional[List[float]]
    row_offset_mm: Optional[float]
    shell_size: str
    mounting_hole_pitch_mm: float
    flange_outer_width_mm: float
    shell_height_mm: Optional[float]
    screw_hole_dia_mm: Optional[float]
    h_pitch_mm: float
    v_pitch_mm: float
    contact_size: str
    numbering_front: str
    numbering_solder: str
    panel_cutout: Optional[Dict[str, float]]
    contact_male_min_mm: Optional[float]
    contact_male_max_mm: Optional[float]
    contact_female_entry_min_mm: Optional[float]
    electrical_max_current_a: Optional[float]
    electrical_dwv_v: Optional[float]
    standards: List[str]


SHELL_GEOMETRY: Dict[str, Dict[str, Dict[str, float]]] = {
    "E": {
        "male": {"opening_top_w": 16.90, "opening_h": 8.30, "flange_h": 12.50},
        "female": {"opening_top_w": 16.30, "opening_h": 7.90, "flange_h": 12.50},
    },
    "A": {
        "male": {"opening_top_w": 25.25, "opening_h": 8.30, "flange_h": 12.50},
        "female": {"opening_top_w": 24.60, "opening_h": 7.90, "flange_h": 12.50},
    },
    "B": {
        "male": {"opening_top_w": 38.95, "opening_h": 8.30, "flange_h": 12.50},
        "female": {"opening_top_w": 38.40, "opening_h": 7.90, "flange_h": 12.50},
    },
    "C": {
        "male": {"opening_top_w": 55.40, "opening_h": 8.30, "flange_h": 12.50},
        "female": {"opening_top_w": 54.80, "opening_h": 7.90, "flange_h": 12.50},
    },
    "D": {
        "male": {"opening_top_w": 52.80, "opening_h": 11.15, "flange_h": 15.30},
        "female": {"opening_top_w": 52.20, "opening_h": 10.90, "flange_h": 15.30},
    },
}


def fmt(x: float) -> str:
    s = f"{x:.2f}"
    return s.rstrip("0").rstrip(".")


def svg_el(tag: str, **attrs) -> ET.Element:
    el = ET.Element(tag)
    for key, value in attrs.items():
        if value is None:
            continue
        el.set(key.replace("_", "-"), str(value))
    return el


def add_line(
    parent: ET.Element,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    sw: float = 0.25,
    dash: str | None = None,
) -> None:
    attrs = {
        "x1": fmt(x1),
        "y1": fmt(y1),
        "x2": fmt(x2),
        "y2": fmt(y2),
        "stroke": "black",
        "stroke_width": fmt(sw),
        "fill": "none",
    }
    if dash:
        attrs["stroke_dasharray"] = dash
    parent.append(svg_el("line", **attrs))


def add_circle(parent: ET.Element, cx: float, cy: float, r: float, sw: float = 0.25, fill: str = "white") -> None:
    parent.append(
        svg_el(
            "circle",
            cx=fmt(cx),
            cy=fmt(cy),
            r=fmt(r),
            stroke="black",
            stroke_width=fmt(sw),
            fill=fill,
        )
    )


def add_text(
    parent: ET.Element,
    x: float,
    y: float,
    text: str,
    size: float = 2.2,
    anchor: str = "middle",
    baseline: str = "middle",
    weight: str | None = None,
) -> None:
    t = svg_el(
        "text",
        x=fmt(x),
        y=fmt(y),
        fill="black",
        font_size=fmt(size),
        text_anchor=anchor,
        dominant_baseline=baseline,
        font_family="Arial, Helvetica, sans-serif",
    )
    if weight:
        t.set("font-weight", weight)
    t.text = text
    parent.append(t)


def add_arrow(parent: ET.Element, x: float, y: float, direction: str, size: float = 0.9) -> None:
    if direction == "left":
        pts = [(x, y), (x + size, y - size / 2), (x + size, y + size / 2)]
    elif direction == "right":
        pts = [(x, y), (x - size, y - size / 2), (x - size, y + size / 2)]
    elif direction == "up":
        pts = [(x, y), (x - size / 2, y + size), (x + size / 2, y + size)]
    elif direction == "down":
        pts = [(x, y), (x - size / 2, y - size), (x + size / 2, y - size)]
    else:
        raise ValueError(direction)

    pts_str = " ".join(f"{fmt(px)},{fmt(py)}" for px, py in pts)
    parent.append(svg_el("polygon", points=pts_str, fill="black", stroke="black", stroke_width="0"))


def rounded_polygon_path(points: Sequence[Point], radius: float) -> str:
    pts = list(points)
    if len(pts) < 3:
        raise ValueError("Need >=3 points")

    def dist(a: Point, b: Point) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def unit(vx: float, vy: float) -> Tuple[float, float]:
        d = math.hypot(vx, vy)
        return (0.0, 0.0) if d == 0 else (vx / d, vy / d)

    n = len(pts)
    cmds: List[str] = []

    for i in range(n):
        p_prev = pts[(i - 1) % n]
        p_curr = pts[i]
        p_next = pts[(i + 1) % n]

        v1x, v1y = p_prev[0] - p_curr[0], p_prev[1] - p_curr[1]
        v2x, v2y = p_next[0] - p_curr[0], p_next[1] - p_curr[1]
        u1x, u1y = unit(v1x, v1y)
        u2x, u2y = unit(v2x, v2y)

        dot = max(-1.0, min(1.0, u1x * u2x + u1y * u2y))
        ang = math.acos(dot)
        if ang == 0:
            continue

        t = radius / math.tan(ang / 2.0)
        t = min(t, dist(p_curr, p_prev) * 0.49, dist(p_curr, p_next) * 0.49)

        p_start = (p_curr[0] + u1x * t, p_curr[1] + u1y * t)
        p_end = (p_curr[0] + u2x * t, p_curr[1] + u2y * t)

        if i == 0:
            cmds.append(f"M {fmt(p_start[0])} {fmt(p_start[1])}")
        else:
            cmds.append(f"L {fmt(p_start[0])} {fmt(p_start[1])}")

        cross = u1x * u2y - u1y * u2x
        sweep = 1 if cross < 0 else 0
        cmds.append(f"A {fmt(radius)} {fmt(radius)} 0 0 {sweep} {fmt(p_end[0])} {fmt(p_end[1])}")

    cmds.append("Z")
    return " ".join(cmds)


def dim_horizontal(parent: ET.Element, x1: float, x2: float, y_dim: float, y_ref: float, text: str) -> None:
    add_line(parent, x1, y_ref, x1, y_dim, sw=0.18)
    add_line(parent, x2, y_ref, x2, y_dim, sw=0.18)
    add_line(parent, x1, y_dim, x2, y_dim, sw=0.18)
    add_arrow(parent, x1, y_dim, "right", size=0.8)
    add_arrow(parent, x2, y_dim, "left", size=0.8)
    add_text(parent, (x1 + x2) / 2, y_dim - 1.2, text, size=2.0, anchor="middle", baseline="alphabetic")


def dim_vertical(parent: ET.Element, y1: float, y2: float, x_dim: float, x_ref: float, text: str) -> None:
    add_line(parent, x_ref, y1, x_dim, y1, sw=0.18)
    add_line(parent, x_ref, y2, x_dim, y2, sw=0.18)
    add_line(parent, x_dim, y1, x_dim, y2, sw=0.18)
    add_arrow(parent, x_dim, y1, "down", size=0.8)
    add_arrow(parent, x_dim, y2, "up", size=0.8)
    add_text(parent, x_dim + 1.2, (y1 + y2) / 2, text, size=2.0, anchor="start", baseline="middle")


def dim_h_simple(parent: ET.Element, x1: float, x2: float, y: float, text: str) -> None:
    add_line(parent, x1, y, x2, y, sw=0.18, dash="2 1")
    add_arrow(parent, x1, y, "right", size=0.75)
    add_arrow(parent, x2, y, "left", size=0.75)
    add_text(parent, (x1 + x2) / 2, y - 1.0, text, size=1.8, anchor="middle", baseline="alphabetic")


def dim_v_simple_left(parent: ET.Element, y1: float, y2: float, x: float, text: str) -> None:
    add_line(parent, x, y1, x, y2, sw=0.18, dash="2 1")
    add_arrow(parent, x, y1, "down", size=0.75)
    add_arrow(parent, x, y2, "up", size=0.75)
    add_text(parent, x - 1.0, (y1 + y2) / 2, text, size=1.8, anchor="end", baseline="middle")


def distribute_pins(pin_count: int, rows: int) -> List[int]:
    if rows == 2:
        return [(pin_count + 1) // 2, pin_count // 2]
    if rows == 3:
        base = pin_count // 3
        rem = pin_count % 3
        counts = [base, base, base]
        if rem == 1:
            counts[1] += 1
        elif rem == 2:
            counts[0] += 1
            counts[2] += 1
        return counts
    if rows == 4:
        base = pin_count // 4
        rem = pin_count % 4
        counts = [base, base, base, base]
        for i in range(rem):
            counts[i] += 1
        return counts
    raise ValueError("rows must be 2, 3, or 4")


def row_offsets_for_counts(counts: List[int], h_pitch: float, stagger: List[float]) -> List[float]:
    non_stagger_indices = [i for i in range(len(counts)) if stagger[i] == 0]
    stagger_indices = [i for i in range(len(counts)) if stagger[i] != 0]

    non_stagger_max = max((counts[i] for i in non_stagger_indices), default=0)
    stagger_max = max((counts[i] for i in stagger_indices), default=0)

    offsets: List[float] = []
    for idx, count in enumerate(counts):
        if stagger[idx] == 0:
            raw_center = ((non_stagger_max - count) * h_pitch) / 2.0
            center_offset = math.floor(raw_center / h_pitch) * h_pitch
        else:
            center_offset = ((stagger_max - count) * h_pitch) / 2.0
        offsets.append(stagger[idx] + center_offset)

    return offsets


def generate_pin_positions(
    pin_count: int,
    rows: int,
    h: float,
    v: float,
    view: str,
    gender: str,
    row_counts: Optional[List[int]] = None,
    row_offsets: Optional[List[float]] = None,
    row_offset_mm: Optional[float] = None,
) -> List[Dict[str, float | int]]:
    counts = row_counts or distribute_pins(pin_count, rows)
    if sum(counts) != pin_count:
        raise ValueError(f"row_counts sum {sum(counts)} != pin_count {pin_count}")
    if len(counts) != rows:
        raise ValueError(f"row_counts length {len(counts)} != rows {rows}")

    if row_offsets is None:
        stagger = [row_offset_mm if (idx % 2 == 1) else 0.0 for idx in range(rows)]
        if row_offset_mm is None:
            stagger = [(h / 2.0 if (idx % 2 == 1) else 0.0) for idx in range(rows)]
        row_offsets = row_offsets_for_counts(counts, h, stagger)
    elif len(row_offsets) != rows:
        raise ValueError(f"row_offsets length {len(row_offsets)} != rows {rows}")

    pins: List[Dict[str, float | int]] = []
    n = 1
    for r, cnt in enumerate(counts):
        for i in range(cnt):
            pins.append({"n": n, "row": r, "x": i * h + row_offsets[r], "y": r * v})
            n += 1

    min_x = min(float(p["x"]) for p in pins)
    max_x = max(float(p["x"]) for p in pins)
    min_y = min(float(p["y"]) for p in pins)
    max_y = max(float(p["y"]) for p in pins)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0

    for p in pins:
        p["x"] = float(p["x"]) - cx
        p["y"] = float(p["y"]) - cy

    # Pin 1 position convention:
    # - Male (plug), mating face: Pin 1 at top-left
    # - Female (receptacle), mating face: Pin 1 at top-right
    if gender == "female":
        for p in pins:
            p["x"] = -float(p["x"])

    # Solder side view is mirrored relative to mating face.
    if view == "solder":
        for p in pins:
            p["x"] = -float(p["x"])

    return pins


def sanitize_stem(stem: str) -> str:
    stem = stem.strip().lower()
    stem = re.sub(r"[^a-z0-9]+", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")
    return stem


def wrap_text(text: str, max_chars: int = 32) -> List[str]:
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def add_info_block(parent: ET.Element, x: float, y: float, title: str, lines: List[str]) -> float:
    if not lines:
        return y
    add_text(parent, x, y, title, size=2.05, anchor="start", baseline="hanging", weight="bold")
    y += 2.9
    for line in lines:
        add_text(parent, x, y, line, size=1.8, anchor="start", baseline="hanging")
        y += 2.4
    return y + 1.4


def generate_svg(spec: DSubSpec, gender: str, view: str, include_caption: bool = True) -> str:
    margin_left, margin_right, margin_top, margin_bottom = 38.0, 148.0, 30.0, 48.0

    outer_w = spec.flange_outer_width_mm
    outer_h = spec.shell_height_mm or SHELL_GEOMETRY[spec.shell_size][gender]["flange_h"]
    opening_top_w = SHELL_GEOMETRY[spec.shell_size][gender]["opening_top_w"]
    opening_h = SHELL_GEOMETRY[spec.shell_size][gender]["opening_h"]
    hole_pitch = spec.mounting_hole_pitch_mm

    width = margin_left + outer_w + margin_right
    height = margin_top + outer_h + margin_bottom

    svg = svg_el(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        width=f"{fmt(width)}mm",
        height=f"{fmt(height)}mm",
        viewBox=f"0 0 {fmt(width)} {fmt(height)}",
    )

    svg.append(svg_el("rect", x="0", y="0", width=fmt(width), height=fmt(height), fill="white"))

    root = svg_el("g")
    svg.append(root)

    layers: Dict[str, ET.Element] = {}

    def layer(layer_id: str) -> ET.Element:
        grp = svg_el("g", data_layer=layer_id)
        layers[layer_id] = grp
        root.append(grp)
        return grp

    g_base = layer("base")
    g_pin_labels = layer("pin_labels")
    g_flange_dim = layer("flange_dimensions")
    g_pitch_dim = layer("pitch_dimensions")
    g_panel_cutout = layer("panel_cutout")
    g_insert_info = layer("insert_info")
    g_contacts_info = layer("contacts_info")
    g_electrical_info = layer("electrical_info")
    g_standards_info = layer("standards_info")
    g_caption = layer("caption")

    ox, oy = margin_left, margin_top
    cx, cy = ox + outer_w / 2.0, oy + outer_h / 2.0

    g_base.append(
        svg_el(
            "rect",
            x=fmt(ox),
            y=fmt(oy),
            width=fmt(outer_w),
            height=fmt(outer_h),
            rx=fmt(1.2),
            ry=fmt(1.2),
            fill="none",
            stroke="black",
            stroke_width=fmt(0.30),
        )
    )

    hole_dia = spec.screw_hole_dia_mm or 4.0
    hole_r = hole_dia / 2.0
    hcx1 = cx - hole_pitch / 2.0
    hcx2 = cx + hole_pitch / 2.0
    add_circle(g_base, hcx1, cy, hole_r, sw=0.25, fill="none")
    add_circle(g_base, hcx2, cy, hole_r, sw=0.25, fill="none")

    pins = generate_pin_positions(
        spec.pin_count,
        spec.rows,
        spec.h_pitch_mm,
        spec.v_pitch_mm,
        view=view,
        gender=gender,
        row_counts=spec.row_counts,
        row_offsets=spec.row_offsets,
        row_offset_mm=spec.row_offset_mm,
    )

    pxs = [float(p["x"]) for p in pins]
    pys = [float(p["y"]) for p in pins]
    pin_min_x, pin_max_x = min(pxs), max(pxs)
    pin_min_y, pin_max_y = min(pys), max(pys)
    pin_w = pin_max_x - pin_min_x
    pin_h = pin_max_y - pin_min_y

    side_angle_deg = 10.0
    clearance_x = 3.0
    clearance_y = 2.8

    opening_h_eff = max(opening_h, pin_h + 2 * clearance_y)
    opening_top_w_eff = max(opening_top_w, pin_w + 2 * clearance_x)

    top_w = min(opening_top_w_eff, outer_w - 6.0)
    bottom_w = top_w - 2.0 * math.tan(math.radians(side_angle_deg)) * opening_h_eff
    bottom_w = max(bottom_w, pin_w + clearance_x)

    top_y = cy - opening_h_eff / 2.0
    bot_y = cy + opening_h_eff / 2.0
    top_half = top_w / 2.0
    bot_half = bottom_w / 2.0

    trap_pts = [
        (cx - top_half, top_y),
        (cx + top_half, top_y),
        (cx + bot_half, bot_y),
        (cx - bot_half, bot_y),
    ]
    corner_r = min(2.2, opening_h_eff * 0.22, top_w * 0.18)
    opening_path = rounded_polygon_path(trap_pts, corner_r)
    g_base.append(svg_el("path", d=opening_path, fill="none", stroke="black", stroke_width=fmt(0.25)))

    pin_r = 0.55 if spec.rows == 2 else (0.45 if spec.rows == 3 else 0.40)
    pin_fill = "black" if gender == "male" else "white"
    for p in pins:
        x = cx + float(p["x"])
        y = cy + float(p["y"])
        add_circle(g_base, x, y, pin_r, sw=0.18, fill=pin_fill)

    label_x_pad = 4.0
    for r in range(spec.rows):
        row_pins = sorted([p for p in pins if int(p["row"]) == r], key=lambda pp: float(pp["x"]))
        left_pin = row_pins[0]
        right_pin = row_pins[-1]
        y = cy + float(left_pin["y"])
        add_text(g_pin_labels, ox - label_x_pad, y, str(int(left_pin["n"])), size=2.2, anchor="end", weight="bold")
        add_text(
            g_pin_labels,
            ox + outer_w + label_x_pad,
            y,
            str(int(right_pin["n"])),
            size=2.2,
            anchor="start",
            weight="bold",
        )

    dim_horizontal(g_flange_dim, ox, ox + outer_w, oy - 16.0, oy, f"{outer_w:.2f} mm")
    dim_horizontal(g_flange_dim, hcx1, hcx2, oy + outer_h + 16.0, cy, f"{hole_pitch:.2f} mm")
    dim_vertical(g_flange_dim, oy, oy + outer_h, ox + outer_w + 12.0, ox + outer_w, f"{outer_h:.2f} mm")

    top_row = sorted([p for p in pins if int(p["row"]) == 0], key=lambda pp: float(pp["x"]))
    if len(top_row) >= 2:
        x1 = cx + float(top_row[0]["x"])
        x2 = cx + float(top_row[1]["x"])
        y = top_y - 3.5
        dim_h_simple(g_pitch_dim, x1, x2, y, f"H pitch={spec.h_pitch_mm:.3f} mm")

    if spec.rows >= 2:
        r0 = sorted([p for p in pins if int(p["row"]) == 0], key=lambda pp: float(pp["x"]))[0]
        r1 = sorted([p for p in pins if int(p["row"]) == 1], key=lambda pp: float(pp["x"]))[0]
        y1 = cy + float(r0["y"])
        y2 = cy + float(r1["y"])
        dim_v_simple_left(g_pitch_dim, y1, y2, ox - 18.0, f"V pitch={spec.v_pitch_mm:.3f} mm")

        dx = abs((cx + float(r1["x"])) - (cx + float(r0["x"])))
        offset_val = spec.row_offset_mm if spec.row_offset_mm is not None else dx
        dim_h_simple(
            g_pitch_dim,
            cx + float(r0["x"]),
            cx + float(r1["x"]),
            cy + opening_h_eff / 2.0 + 7.5,
            f"Row offset={offset_val:.3f} mm",
        )

    info_x = ox + outer_w + 26.0

    row_counts_txt = "-".join(str(v) for v in (spec.row_counts or []))
    insert_lines = [
        f"Density: {spec.density}",
        f"Rows: {spec.rows} ({row_counts_txt})",
        f"Contact size: {spec.contact_size}",
        f"Pitch X/Y: {spec.h_pitch_mm:.3f}/{spec.v_pitch_mm:.3f} mm",
    ]
    if spec.row_offset_mm is not None:
        insert_lines.append(f"Offset: {spec.row_offset_mm:.3f} mm")
    if spec.numbering_front:
        insert_lines.extend(wrap_text(f"Front: {spec.numbering_front}", max_chars=34)[:2])
    cursor_y = add_info_block(g_insert_info, info_x, oy + 0.8, "Insert", insert_lines)

    contact_lines: List[str] = []
    if spec.contact_male_min_mm is not None and spec.contact_male_max_mm is not None:
        contact_lines.append(f"Male pin: {spec.contact_male_min_mm:.3f}-{spec.contact_male_max_mm:.3f} mm")
    if spec.contact_female_entry_min_mm is not None:
        contact_lines.append(f"Female entry >= {spec.contact_female_entry_min_mm:.3f} mm")
    cursor_y = add_info_block(g_contacts_info, info_x, cursor_y, "Contacts", contact_lines)

    electrical_lines: List[str] = []
    if spec.electrical_max_current_a is not None:
        electrical_lines.append(f"Current: {spec.electrical_max_current_a:.1f} A/contact")
    if spec.electrical_dwv_v is not None:
        electrical_lines.append(f"DWV: {spec.electrical_dwv_v:.0f} V RMS")
    cursor_y = add_info_block(g_electrical_info, info_x, cursor_y, "Electrical", electrical_lines)

    standards_lines: List[str] = []
    for std in spec.standards:
        standards_lines.extend(wrap_text(std, max_chars=34))
    cursor_y = add_info_block(g_standards_info, info_x, cursor_y, "Standards", standards_lines)

    if spec.panel_cutout:
        panel = spec.panel_cutout
        panel_lines = [
            (
                f"T/B/H: {panel['top_width']:.2f}/"
                f"{panel['bottom_width']:.2f}/"
                f"{panel['height']:.2f} mm"
            ),
        ]
        radius = panel.get("corner_radius")
        if radius is not None:
            panel_lines.append(f"Angle {panel['side_angle_deg']:.1f} deg, R {radius:.2f} mm")
        add_info_block(g_panel_cutout, info_x, cursor_y, "Panel cutout", panel_lines)

    if include_caption:
        add_text(
            g_caption,
            cx,
            oy + outer_h + margin_bottom - 8.0,
            f"{spec.designation} - {gender} - {view}",
            size=2.2,
            anchor="middle",
            baseline="middle",
        )

    return ET.tostring(svg, encoding="unicode")


def validate_connector(item: dict[str, Any]) -> List[str]:
    errors = []
    cid = item.get("id", "unknown")
    insert = item.get("insert") or {}
    pins = int(insert.get("total_contacts") or 0)
    row_counts = [int(v) for v in (insert.get("contacts_per_row") or [])]
    rows = int(insert.get("rows") or len(row_counts))

    if row_counts and sum(row_counts) != pins:
        errors.append(f"{cid}: sum(contacts_per_row)={sum(row_counts)} != total_contacts={pins}")

    if row_counts and rows != len(row_counts):
        errors.append(f"{cid}: rows={rows} != len(contacts_per_row)={len(row_counts)}")

    return errors


def load_specs(catalog: Optional[dict[str, Any]] = None) -> List[DSubSpec]:
    resolved_catalog = catalog or build_catalog()

    all_errors: List[str] = []
    for item in resolved_catalog.get("connectors", []):
        all_errors.extend(validate_connector(item))
    if all_errors:
        print("Catalog validation errors:")
        for err in all_errors:
            print(f"  - {err}")
        raise SystemExit("Fix catalog errors before generating SVGs")

    specs: List[DSubSpec] = []
    for item in resolved_catalog.get("connectors", []):
        insert = item.get("insert") or {}
        shell = item.get("shell") or {}
        flange = shell.get("flange") or {}
        contacts = item.get("contacts") or {}
        electrical = item.get("electrical") or {}

        male = contacts.get("male_pin_diameter_mm") or {}
        female = contacts.get("female_entry_diameter_mm") or {}

        specs.append(
            DSubSpec(
                label=item.get("name") or item.get("designation") or item.get("id"),
                designation=item.get("designation") or item.get("id"),
                density=item.get("density") or "standard",
                file_tag=item.get("asset_tag") or item.get("id"),
                pin_count=int(insert.get("total_contacts")),
                rows=int(insert.get("rows")),
                row_counts=insert.get("contacts_per_row"),
                row_offsets=item.get("row_offsets"),
                row_offset_mm=insert.get("row_offset_mm"),
                shell_size=shell.get("letter"),
                mounting_hole_pitch_mm=float(flange.get("mounting_hole_spacing_mm")),
                flange_outer_width_mm=float(flange.get("outer_width_mm")),
                shell_height_mm=float(flange.get("outer_height_mm")),
                screw_hole_dia_mm=float(flange.get("mounting_hole_diameter_mm")),
                h_pitch_mm=float((insert.get("pitch_mm") or {}).get("x")),
                v_pitch_mm=float((insert.get("pitch_mm") or {}).get("y")),
                contact_size=str(insert.get("contact_size") or "20"),
                numbering_front=str((insert.get("numbering") or {}).get("front_view") or ""),
                numbering_solder=str((insert.get("numbering") or {}).get("solder_side_view") or ""),
                panel_cutout=shell.get("panel_cutout_trapezoid_mm"),
                contact_male_min_mm=(float(male.get("min")) if male.get("min") is not None else None),
                contact_male_max_mm=(float(male.get("max")) if male.get("max") is not None else None),
                contact_female_entry_min_mm=(float(female.get("min")) if female.get("min") is not None else None),
                electrical_max_current_a=(
                    float(electrical.get("max_current_a_per_contact"))
                    if electrical.get("max_current_a_per_contact") is not None
                    else None
                ),
                electrical_dwv_v=(
                    float(electrical.get("dielectric_withstand_v_rms_60hz_sea_level"))
                    if electrical.get("dielectric_withstand_v_rms_60hz_sea_level") is not None
                    else None
                ),
                standards=[str(v) for v in (item.get("standards") or [])],
            )
        )

    return specs


def generate_all(out_dir: Path, catalog: Optional[dict[str, Any]] = None, include_caption: bool = True) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    genders = ["male", "female"]
    views = ["outside", "solder"]

    written = 0
    for spec in load_specs(catalog):
        for gender in genders:
            for view in views:
                svg = generate_svg(spec, gender, view, include_caption=include_caption)
                stem = sanitize_stem(f"{spec.file_tag}_{gender}_{view}")
                fpath = out_dir / f"{stem}.svg"
                fpath.write_text(svg, encoding="utf-8")
                written += 1
    return written


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate D-Sub connector SVGs.")
    parser.add_argument("--out", default="dist/assets/svg", help="Output directory")
    parser.add_argument("--no-caption", action="store_true", help="Disable caption text")
    args = parser.parse_args()

    out_dir = Path(args.out)
    written = generate_all(out_dir, include_caption=not args.no_caption)
    print(f"Wrote {written} SVG files to: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
