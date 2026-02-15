const catalogPath = "data/catalog.json";
const svgBasePath = "assets/svg";
const NOTES_STORAGE_KEY = "dsub-connector-notes";
const LAYER_PREFS_KEY = "dsub-layer-visibility";

const elType = document.getElementById("selType");
const elGender = document.getElementById("selGender");
const elView = document.getElementById("selView");
const elPreview = document.getElementById("preview");
const elStatus = document.getElementById("status");
const elSpecInfo = document.getElementById("specInfo");
const elNotesArea = document.getElementById("notesArea");
const elNotesStatus = document.getElementById("notesStatus");
const elLayerControls = document.getElementById("layerControls");

const btnOpenSvg = document.getElementById("btnOpenSvg");
const btnDownloadSvg = document.getElementById("btnDownloadSvg");

const svgCache = new Map();
let catalog = null;
let saveTimeout = null;
let layerPrefs = {};

function setStatus(message, level = "") {
  elStatus.className = "status" + (level ? ` ${level}` : "");
  elStatus.textContent = message;
}

function optionize(select, items, getId, getName) {
  select.innerHTML = "";
  for (const it of items) {
    const opt = document.createElement("option");
    opt.value = getId(it);
    opt.textContent = getName(it);
    select.appendChild(opt);
  }
}

function sanitizeAssetTag(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function formatNumber(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toFixed(digits);
}

function getCurrentSpec() {
  if (!catalog) return null;
  return catalog.connectors.find((c) => c.id === elType.value) || null;
}

function getCurrentAssetKey() {
  const spec = getCurrentSpec();
  if (!spec) return null;
  const base = spec.asset_tag || sanitizeAssetTag(spec.id);
  return `${base}_${elGender.value}_${elView.value}`;
}

function getNotesKey() {
  const spec = getCurrentSpec();
  return spec ? spec.id : null;
}

function loadAllNotes() {
  try {
    const stored = localStorage.getItem(NOTES_STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
}

function saveAllNotes(notes) {
  try {
    localStorage.setItem(NOTES_STORAGE_KEY, JSON.stringify(notes));
    return true;
  } catch {
    return false;
  }
}

function loadNotesForConnector() {
  const key = getNotesKey();
  if (!key) {
    elNotesArea.value = "";
    return;
  }
  const allNotes = loadAllNotes();
  elNotesArea.value = allNotes[key] || "";
  elNotesStatus.textContent = "";
  elNotesStatus.className = "notes-status";
}

function saveNotesForConnector() {
  const key = getNotesKey();
  if (!key) return;

  const allNotes = loadAllNotes();
  const currentText = elNotesArea.value.trim();

  if (currentText) {
    allNotes[key] = currentText;
  } else {
    delete allNotes[key];
  }

  if (saveAllNotes(allNotes)) {
    elNotesStatus.textContent = "Saved";
    elNotesStatus.className = "notes-status saved";
    setTimeout(() => {
      elNotesStatus.textContent = "";
      elNotesStatus.className = "notes-status";
    }, 2000);
  }
}

function scheduleNoteSave() {
  if (saveTimeout) {
    clearTimeout(saveTimeout);
  }
  elNotesStatus.textContent = "Saving...";
  elNotesStatus.className = "notes-status";
  saveTimeout = setTimeout(() => {
    saveNotesForConnector();
    saveTimeout = null;
  }, 500);
}

function loadLayerPrefs() {
  try {
    const stored = localStorage.getItem(LAYER_PREFS_KEY);
    layerPrefs = stored ? JSON.parse(stored) : {};
  } catch {
    layerPrefs = {};
  }
}

function saveLayerPrefs() {
  try {
    localStorage.setItem(LAYER_PREFS_KEY, JSON.stringify(layerPrefs));
  } catch {
    // Ignore storage errors; visibility still works for this session.
  }
}

function getLayers() {
  if (catalog?.layers?.length) return catalog.layers;
  return [];
}

function isLayerEnabled(layer) {
  if (Object.prototype.hasOwnProperty.call(layerPrefs, layer.id)) {
    return Boolean(layerPrefs[layer.id]);
  }
  return layer.default_enabled !== false;
}

function applyLayerVisibility() {
  const svg = elPreview.querySelector("svg");
  if (!svg) return;

  for (const layer of getLayers()) {
    const visible = isLayerEnabled(layer);
    const nodes = svg.querySelectorAll(`[data-layer="${layer.id}"]`);
    for (const node of nodes) {
      node.style.display = visible ? "" : "none";
    }
  }
}

function renderLayerControls() {
  const layers = getLayers();
  elLayerControls.innerHTML = "";
  if (!layers.length) {
    return;
  }

  for (const layer of layers) {
    const id = `layer_${layer.id}`;
    const label = document.createElement("label");
    label.className = "layer-option";
    label.setAttribute("for", id);

    const input = document.createElement("input");
    input.type = "checkbox";
    input.id = id;
    input.checked = isLayerEnabled(layer);
    input.addEventListener("change", () => {
      layerPrefs[layer.id] = input.checked;
      saveLayerPrefs();
      applyLayerVisibility();
    });

    const text = document.createElement("span");
    text.textContent = layer.name || layer.id;

    label.appendChild(input);
    label.appendChild(text);
    elLayerControls.appendChild(label);
  }
}

async function loadCatalog() {
  const res = await fetch(catalogPath);
  if (!res.ok) {
    throw new Error(`Failed to load catalog: ${res.status}`);
  }
  return res.json();
}

async function loadSvgText(key) {
  if (svgCache.has(key)) {
    return svgCache.get(key);
  }
  const res = await fetch(`${svgBasePath}/${key}.svg`);
  if (!res.ok) {
    return null;
  }
  const text = await res.text();
  svgCache.set(key, text);
  return text;
}

function updateSpecInfo() {
  const spec = getCurrentSpec();
  if (!spec) {
    elSpecInfo.textContent = "";
    return;
  }

  const insert = spec.insert || {};
  const counts = Array.isArray(insert.contacts_per_row) ? insert.contacts_per_row.join("-") : "n/a";
  const shell = spec.shell?.letter || "?";
  const px = formatNumber(insert.pitch_mm?.x);
  const py = formatNumber(insert.pitch_mm?.y);

  elSpecInfo.textContent = `${insert.total_contacts || "?"} pins | ${insert.rows || "?"} rows (${counts}) | shell ${shell} | pitch ${px}/${py} mm`;
}

function getVisibleSvgText() {
  const svg = elPreview.querySelector("svg");
  if (!svg) return null;
  const serializer = new XMLSerializer();
  return serializer.serializeToString(svg);
}

async function render() {
  const key = getCurrentAssetKey();
  if (!key) return;

  updateSpecInfo();
  loadNotesForConnector();
  setStatus("Loading SVG...", "");

  const svgText = await loadSvgText(key);
  if (!svgText) {
    elPreview.innerHTML = "";
    setStatus("No SVG found for this combination.", "warn");
    return;
  }

  elPreview.innerHTML = svgText;
  applyLayerVisibility();
  setStatus(`Loaded: ${key}`, "ok");
}

async function openSvg() {
  const visibleSvg = getVisibleSvgText();
  const key = getCurrentAssetKey();
  if (!key) return;

  const svgText = visibleSvg || (await loadSvgText(key));
  if (!svgText) return;

  const blob = new Blob([svgText], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

async function downloadSvg() {
  const visibleSvg = getVisibleSvgText();
  const key = getCurrentAssetKey();
  if (!key) return;

  const svgText = visibleSvg || (await loadSvgText(key));
  if (!svgText) return;

  const blob = new Blob([svgText], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${key}.svg`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

async function init() {
  try {
    catalog = await loadCatalog();
  } catch (err) {
    setStatus("Failed to load catalog data.", "warn");
    return;
  }

  loadLayerPrefs();

  optionize(elType, catalog.connectors, (x) => x.id, (x) => x.name || x.designation || x.id);
  optionize(elGender, catalog.genders, (x) => x.id, (x) => x.name);
  optionize(elView, catalog.views, (x) => x.id, (x) => x.name);

  renderLayerControls();

  elType.addEventListener("change", render);
  elGender.addEventListener("change", render);
  elView.addEventListener("change", render);

  elNotesArea.addEventListener("input", scheduleNoteSave);

  btnOpenSvg.addEventListener("click", () => openSvg().catch(console.error));
  btnDownloadSvg.addEventListener("click", () => downloadSvg().catch(console.error));

  await render();
}

document.addEventListener("DOMContentLoaded", () => {
  init().catch(console.error);
});
