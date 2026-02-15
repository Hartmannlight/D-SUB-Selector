#!/usr/bin/env python3
"""
Build a normalized catalog from D-Sub-info.md YAML snippets.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = PROJECT_ROOT / "D-Sub-info.md"

DISPLAY_NAME_BY_ID = {
    "de-9-standard": "DE-9 (Standard)",
    "da-15-standard": "DA-15 (Standard)",
    "db-25-standard": "DB-25 (Standard)",
    "dc-37-standard": "DC-37 (Standard)",
    "dd-50-standard": "DD-50 (Standard)",
    "de-15-hd": "DE-15 (HD15)",
    "da-26-hd": "DA-26 (HD26)",
    "db-44-hd": "DB-44 (HD44)",
    "dc-62-hd": "DC-62 (HD62)",
    "dd-78-hd": "DD-78 (HD78)",
}

USAGE_BY_ID = {
    "de-9-standard": "RS-232, legacy video, CAN, joysticks",
    "da-15-standard": "AUI, legacy RGB, gameport",
    "db-25-standard": "RS-232, parallel, SCSI, pro audio",
    "dc-37-standard": "multi I/O, instrumentation",
    "dd-50-standard": "early SCSI, control/measurement",
    "de-15-hd": "VGA",
    "da-26-hd": "industrial / automation",
    "db-44-hd": "DAQ / AV / control",
    "dc-62-hd": "measurement / robotics",
    "dd-78-hd": "high channel-count systems",
}

SHELL_DEFAULTS = {
    "E": {
        "mil_shell_size": 1,
        "flange": {
            "outer_width_mm": 30.81,
            "outer_height_mm": 12.55,
            "mounting_hole_spacing_mm": 24.99,
            "mounting_hole_diameter_mm": 3.05,
        },
        "panel_cutout_trapezoid_mm": {
            "top_width": 12.49,
            "bottom_width": 19.74,
            "height": 11.18,
            "side_angle_deg": 10.0,
            "corner_radius": 3.81,
        },
    },
    "A": {
        "mil_shell_size": 2,
        "flange": {
            "outer_width_mm": 39.14,
            "outer_height_mm": 12.55,
            "mounting_hole_spacing_mm": 33.32,
            "mounting_hole_diameter_mm": 3.05,
        },
        "panel_cutout_trapezoid_mm": {
            "top_width": 16.66,
            "bottom_width": 28.07,
            "height": 11.18,
            "side_angle_deg": 10.0,
            "corner_radius": 3.81,
        },
    },
    "B": {
        "mil_shell_size": 3,
        "flange": {
            "outer_width_mm": 53.04,
            "outer_height_mm": 12.55,
            "mounting_hole_spacing_mm": 47.04,
            "mounting_hole_diameter_mm": 3.05,
        },
        "panel_cutout_trapezoid_mm": {
            "top_width": 24.99,
            "bottom_width": 41.53,
            "height": 11.18,
            "side_angle_deg": 10.0,
            "corner_radius": 3.81,
        },
    },
    "C": {
        "mil_shell_size": 4,
        "flange": {
            "outer_width_mm": 69.32,
            "outer_height_mm": 12.55,
            "mounting_hole_spacing_mm": 63.50,
            "mounting_hole_diameter_mm": 3.05,
        },
        "panel_cutout_trapezoid_mm": {
            "top_width": 33.32,
            "bottom_width": 54.84,
            "height": 11.18,
            "side_angle_deg": 10.0,
            "corner_radius": 3.81,
        },
    },
    "D": {
        "mil_shell_size": 5,
        "flange": {
            "outer_width_mm": 66.93,
            "outer_height_mm": 15.37,
            "mounting_hole_spacing_mm": 61.11,
            "mounting_hole_diameter_mm": 3.05,
        },
        "panel_cutout_trapezoid_mm": {
            "top_width": 30.55,
            "bottom_width": 55.63,
            "height": 13.97,
            "side_angle_deg": 10.0,
            "corner_radius": 3.81,
        },
    },
}

CONTACT_DEFAULTS = {
    "20": {
        "male_pin_diameter_mm": {"min": 0.991, "max": 1.041},
        "female_entry_diameter_mm": {"min": 1.067},
    },
    "22D": {
        "male_pin_diameter_mm": {"min": 0.749, "max": 0.775},
        "female_entry_diameter_mm": {"min": 0.876},
    },
}

DEFAULT_STANDARDS = ["MIL-DTL-24308", "IEC 60807-2", "DIN 41652"]
DEFAULT_DWV = 1000
DEFAULT_CURRENT_BY_DENSITY = {
    "standard": 5,
    "high_density": 3,
}

LAYERS = [
    {"id": "pin_labels", "name": "Pin labels", "default_enabled": True},
    {"id": "flange_dimensions", "name": "Flange dimensions", "default_enabled": True},
    {"id": "pitch_dimensions", "name": "Pitch dimensions", "default_enabled": True},
    {"id": "panel_cutout", "name": "Panel cutout", "default_enabled": False},
    {"id": "insert_info", "name": "Insert data", "default_enabled": True},
    {"id": "contacts_info", "name": "Contact data", "default_enabled": False},
    {"id": "electrical_info", "name": "Electrical data", "default_enabled": False},
    {"id": "standards_info", "name": "Standards", "default_enabled": False},
    {"id": "caption", "name": "Caption", "default_enabled": True},
]

GENDERS = [
    {"id": "male", "name": "Male (plug)"},
    {"id": "female", "name": "Female (receptacle)"},
]

VIEWS = [
    {"id": "outside", "name": "Outside (mating face)"},
    {"id": "solder", "name": "Solder side (rear view)"},
]


def _sanitize_asset_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _extract_yaml_docs(report_text: str) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for block in re.findall(r"```yaml\s*(.*?)```", report_text, flags=re.S):
        parsed = yaml.safe_load(block)
        if isinstance(parsed, dict):
            docs.append(parsed)
    return docs


def _distribute_contacts(total_contacts: int, rows: int) -> list[int]:
    if rows <= 0:
        return []
    base = total_contacts // rows
    rem = total_contacts % rows
    counts = [base] * rows
    for idx in range(rem):
        counts[idx] += 1
    return counts


def _normalize_insert(raw_insert: dict[str, Any]) -> dict[str, Any]:
    counts = [int(v) for v in (raw_insert.get("contacts_per_row") or [])]
    rows = _to_int(raw_insert.get("rows")) or len(counts)
    total_contacts = _to_int(raw_insert.get("total_contacts")) or sum(counts)
    if not counts and total_contacts and rows:
        counts = _distribute_contacts(total_contacts, rows)

    if rows and len(counts) != rows:
        raise SystemExit(f"Invalid contacts_per_row length for rows={rows}: {counts}")
    if total_contacts and sum(counts) != total_contacts:
        raise SystemExit(f"Invalid contact sum for total_contacts={total_contacts}: {counts}")

    pitch = raw_insert.get("pitch_mm") or {}
    pitch_x = _to_float(pitch.get("x"))
    pitch_y = _to_float(pitch.get("y"))
    row_offset = _to_float(raw_insert.get("row_offset_mm"))
    if row_offset is None and pitch_x is not None and rows and rows > 1:
        row_offset = round(pitch_x / 2.0, 3)

    numbering = raw_insert.get("numbering") or {}
    front_view = ""
    solder_side_view = ""
    if isinstance(numbering, str):
        front_view = numbering
    elif isinstance(numbering, dict):
        front_view = str(numbering.get("front_view") or "")
        solder_side_view = str(numbering.get("solder_side_view") or "")

    return {
        "total_contacts": int(total_contacts),
        "contact_size": str(raw_insert.get("contact_size") or "20"),
        "rows": int(rows),
        "contacts_per_row": counts,
        "pitch_mm": {"x": pitch_x, "y": pitch_y},
        "row_offset_mm": row_offset,
        "numbering": {
            "front_view": front_view,
            "solder_side_view": solder_side_view,
        },
    }


def _normalize_flange(raw_connector: dict[str, Any], shell_letter: str) -> dict[str, Any]:
    defaults = SHELL_DEFAULTS[shell_letter]["flange"]
    raw_flange = raw_connector.get("flange") or {}
    outer_mm = raw_flange.get("outer_mm")

    width = _to_float(defaults["outer_width_mm"])
    height = _to_float(defaults["outer_height_mm"])
    if isinstance(outer_mm, list) and len(outer_mm) >= 2:
        width = _to_float(outer_mm[0])
        height = _to_float(outer_mm[1])

    spacing = _to_float(raw_flange.get("mounting_hole_spacing_mm"))
    if spacing is None:
        spacing = _to_float(defaults["mounting_hole_spacing_mm"])

    diameter = _to_float(raw_flange.get("mounting_hole_diameter_mm"))
    if diameter is None:
        diameter = _to_float(defaults["mounting_hole_diameter_mm"])

    return {
        "outer_width_mm": width,
        "outer_height_mm": height,
        "mounting_hole_spacing_mm": spacing,
        "mounting_hole_diameter_mm": diameter,
    }


def _normalize_panel(raw_connector: dict[str, Any], shell_letter: str) -> dict[str, Any]:
    defaults = SHELL_DEFAULTS[shell_letter]["panel_cutout_trapezoid_mm"]
    raw_panel = raw_connector.get("panel_cutout_trapezoid_mm") or {}

    return {
        "top_width": _to_float(raw_panel.get("top_width")) or _to_float(defaults["top_width"]),
        "bottom_width": _to_float(raw_panel.get("bottom_width")) or _to_float(defaults["bottom_width"]),
        "height": _to_float(raw_panel.get("height")) or _to_float(defaults["height"]),
        "side_angle_deg": _to_float(raw_panel.get("side_angle_deg")) or _to_float(defaults["side_angle_deg"]),
        "corner_radius": _to_float(raw_panel.get("corner_radius")) or _to_float(defaults["corner_radius"]),
    }


def _normalize_contacts(raw_connector: dict[str, Any], contact_size: str) -> dict[str, Any]:
    defaults = CONTACT_DEFAULTS.get(contact_size, CONTACT_DEFAULTS["20"])
    raw_contacts = raw_connector.get("contacts") or {}

    male = raw_contacts.get("male_pin_diameter_mm") or defaults["male_pin_diameter_mm"]
    female = raw_contacts.get("female_entry_diameter_mm") or defaults["female_entry_diameter_mm"]

    return {
        "male_pin_diameter_mm": {
            "min": _to_float(male.get("min")),
            "max": _to_float(male.get("max")),
        },
        "female_entry_diameter_mm": {
            "min": _to_float(female.get("min")),
        },
    }


def _normalize_electrical(raw_connector: dict[str, Any], density: str) -> dict[str, Any]:
    raw = raw_connector.get("electrical") or {}
    current = _to_float(raw.get("max_current_a_per_contact"))
    if current is None:
        current = DEFAULT_CURRENT_BY_DENSITY.get(density, 3)

    dwv = _to_float(raw.get("dielectric_withstand_v_rms_60hz_sea_level"))
    if dwv is None:
        dwv = DEFAULT_DWV

    return {
        "max_current_a_per_contact": current,
        "dielectric_withstand_v_rms_60hz_sea_level": dwv,
    }


def _normalize_connector(raw_connector: dict[str, Any]) -> dict[str, Any]:
    connector_id = str(raw_connector.get("id") or "").strip()
    if not connector_id:
        raise SystemExit("Encountered connector entry without id in D-Sub-info.md")

    shell = raw_connector.get("shell") or {}
    shell_letter = str(shell.get("letter") or "").strip().upper()
    if shell_letter not in SHELL_DEFAULTS:
        raise SystemExit(f"Connector {connector_id} references unknown shell letter: {shell_letter}")

    insert = _normalize_insert(raw_connector.get("insert") or {})
    density = str(raw_connector.get("density") or "standard")

    shell_defaults = SHELL_DEFAULTS[shell_letter]
    mil_shell_size = _to_int(shell.get("mil_shell_size")) or shell_defaults["mil_shell_size"]

    standards = raw_connector.get("standards")
    if not isinstance(standards, list) or not standards:
        standards = list(DEFAULT_STANDARDS)

    connector = {
        "id": connector_id,
        "asset_tag": _sanitize_asset_tag(connector_id),
        "name": DISPLAY_NAME_BY_ID.get(connector_id, str(raw_connector.get("designation") or connector_id)),
        "designation": str(raw_connector.get("designation") or connector_id.upper()),
        "family": str(raw_connector.get("family") or "d-subminiature"),
        "density": density,
        "usage": USAGE_BY_ID.get(connector_id, ""),
        "shell": {
            "letter": shell_letter,
            "mil_shell_size": mil_shell_size,
            "flange": _normalize_flange(raw_connector, shell_letter),
            "panel_cutout_trapezoid_mm": _normalize_panel(raw_connector, shell_letter),
        },
        "insert": insert,
        "contacts": _normalize_contacts(raw_connector, insert["contact_size"]),
        "electrical": _normalize_electrical(raw_connector, density),
        "standards": [str(s) for s in standards],
    }

    return connector


def build_catalog(report_path: Path | None = None) -> dict[str, Any]:
    report = report_path or DEFAULT_REPORT_PATH
    if not report.exists():
        raise SystemExit(f"Missing report file: {report}")

    report_text = report.read_text(encoding="utf-8")
    docs = _extract_yaml_docs(report_text)

    by_id: dict[str, dict[str, Any]] = {}
    for doc in docs:
        connector_id = doc.get("id")
        if isinstance(connector_id, str) and connector_id:
            by_id[connector_id] = doc

    connectors = [_normalize_connector(doc) for doc in by_id.values()]

    expected = set(DISPLAY_NAME_BY_ID)
    found = {c["id"] for c in connectors}
    missing = sorted(expected - found)
    if missing:
        raise SystemExit(f"Missing connector definitions in report: {', '.join(missing)}")

    return {
        "schema_version": 2,
        "source": {
            "type": "markdown_yaml",
            "path": str(report.relative_to(PROJECT_ROOT)),
        },
        "layers": LAYERS,
        "connectors": connectors,
        "genders": GENDERS,
        "views": VIEWS,
    }


if __name__ == "__main__":
    import json

    catalog = build_catalog()
    print(json.dumps(catalog, indent=2, ensure_ascii=False))
