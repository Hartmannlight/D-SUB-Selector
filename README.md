# D-Sub Selector

Static site that generates technical SVG drawings for D-Sub connectors and serves them via GitHub Pages.

Catalog data is now sourced from `D-Sub-info.md` (YAML snippets in the report) and normalized during the build.

## Layout
- `src/` site sources (HTML/CSS/JS + catalog data)
- `scripts/` build tools (SVG generator + build script)
- `dist/` build output (generated)
- `legacy/` previous experiments kept for reference

## Build
```bash
python scripts/build.py
```

The build copies `src/` into `dist/` (or `dist_build_<timestamp>` if `dist/` is locked), then:
- generates a normalized catalog at `dist/data/catalog.json`
- generates SVG assets at `dist/assets/svg/`

Each SVG contains toggleable data layers (dimensions, cutout, electrical/standards blocks, etc.) that the UI can show/hide.

## Local preview
Open `dist/index.html` in a browser after building.
