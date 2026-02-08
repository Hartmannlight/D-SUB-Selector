# D-Sub Selector

Static site that generates technical SVG drawings for D-Sub connectors and serves them via GitHub Pages.

## Layout
- `src/` site sources (HTML/CSS/JS + catalog data)
- `scripts/` build tools (SVG generator + build script)
- `dist/` build output (generated)
- `legacy/` previous experiments kept for reference

## Build
```bash
python scripts/build.py
```

The build copies `src/` into `dist/` and generates SVG assets into `dist/assets/svg/`.

## Local preview
Open `dist/index.html` in a browser after building.
