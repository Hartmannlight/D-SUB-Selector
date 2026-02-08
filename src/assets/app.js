const catalogPath = "data/catalog.json";
const svgBasePath = "assets/svg";

const elType = document.getElementById("selType");
const elGender = document.getElementById("selGender");
const elView = document.getElementById("selView");
const elPreview = document.getElementById("preview");
const elStatus = document.getElementById("status");
const elSpecInfo = document.getElementById("specInfo");

const btnOpenSvg = document.getElementById("btnOpenSvg");
const btnDownloadSvg = document.getElementById("btnDownloadSvg");

const svgCache = new Map();
let catalog = null;

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

function getCurrentKey() {
  if (!catalog) return null;
  return `${elType.value}_${elGender.value}_${elView.value}`;
}

function getCurrentSpec() {
  if (!catalog) return null;
  return catalog.connectors.find((c) => c.id === elType.value) || null;
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
  elSpecInfo.textContent = `${spec.pins} pins · ${spec.rows} rows · ${spec.shell} shell`;
}

async function render() {
  const key = getCurrentKey();
  if (!key) return;

  updateSpecInfo();
  setStatus("Loading SVG...", "");

  const svgText = await loadSvgText(key);
  if (!svgText) {
    elPreview.innerHTML = "";
    setStatus("No SVG found for this combination.", "warn");
    return;
  }

  elPreview.innerHTML = svgText;
  setStatus(`Loaded: ${key}`, "ok");
}

async function openSvg() {
  const key = getCurrentKey();
  if (!key) return;
  const svgText = await loadSvgText(key);
  if (!svgText) return;

  const blob = new Blob([svgText], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

async function downloadSvg() {
  const key = getCurrentKey();
  if (!key) return;
  const svgText = await loadSvgText(key);
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

  optionize(elType, catalog.connectors, (x) => x.id, (x) => `${x.name} (${x.pins})`);
  optionize(elGender, catalog.genders, (x) => x.id, (x) => x.name);
  optionize(elView, catalog.views, (x) => x.id, (x) => x.name);

  elType.addEventListener("change", render);
  elGender.addEventListener("change", render);
  elView.addEventListener("change", render);

  btnOpenSvg.addEventListener("click", () => openSvg().catch(console.error));
  btnDownloadSvg.addEventListener("click", () => downloadSvg().catch(console.error));

  await render();
}

document.addEventListener("DOMContentLoaded", () => {
  init().catch(console.error);
});
