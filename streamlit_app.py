"""Comic book flipbook embedded in a Streamlit app via st.components.v1.html.

Two viewing modes:
- Page mode (default): full page fits to the viewport, with 3D page-turn animation.
- Guided/Read mode: page scales to fill the screen width; each tap pans vertically
  by ~80% of the viewport height, and advances to the next page when scrolled past
  the bottom. Designed for comfortable reading on a phone.

Inlines the PNGs as base64 data URLs so the iframe is fully self-contained.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


PAGES = [
    ("p.2.png", "p. 2"),
    ("p.3-p4.png", "p. 3-4"),
    ("p.5.png", "p. 5"),
    ("p.6.png", "p. 6"),
    ("p.7.png", "p. 7"),
]

# Read-mode stops per page. Each stop is a rectangle on the page in fractions
# (x, y, w, h in 0..1). The reader walks these one tap at a time.
STOPS = {
    # p.2: 4 horizontal stripes (Earth / skyline / street / cyber crowd)
    "p.2.png": [
        {"x": 0.02, "y": 0.02, "w": 0.96, "h": 0.21},
        {"x": 0.02, "y": 0.23, "w": 0.96, "h": 0.22},
        {"x": 0.02, "y": 0.45, "w": 0.96, "h": 0.22},
        {"x": 0.02, "y": 0.66, "w": 0.96, "h": 0.34},
    ],
    # p.3-p4: wide spread split into 4 quadrants
    "p.3-p4.png": [
        {"x": 0.00, "y": 0.00, "w": 0.50, "h": 0.50},  # top-left
        {"x": 0.50, "y": 0.00, "w": 0.50, "h": 0.50},  # top-right
        {"x": 0.00, "y": 0.50, "w": 0.50, "h": 0.50},  # bottom-left
        {"x": 0.50, "y": 0.50, "w": 0.50, "h": 0.50},  # bottom-right
    ],
    # p.5, p.6, p.7: split into thirds vertically (full width)
    "p.5.png": [
        {"x": 0.00, "y": 0.00, "w": 1.00, "h": 0.34},
        {"x": 0.00, "y": 0.33, "w": 1.00, "h": 0.34},
        {"x": 0.00, "y": 0.66, "w": 1.00, "h": 0.34},
    ],
    "p.6.png": [
        {"x": 0.00, "y": 0.00, "w": 1.00, "h": 0.34},
        {"x": 0.00, "y": 0.33, "w": 1.00, "h": 0.34},
        {"x": 0.00, "y": 0.66, "w": 1.00, "h": 0.34},
    ],
    "p.7.png": [
        {"x": 0.00, "y": 0.00, "w": 1.00, "h": 0.34},
        {"x": 0.00, "y": 0.33, "w": 1.00, "h": 0.34},
        {"x": 0.00, "y": 0.66, "w": 1.00, "h": 0.34},
    ],
}

ASSET_DIR = Path(__file__).parent


def encode_page(filename: str) -> str:
    path = ASSET_DIR / filename
    if not path.exists():
        st.error(f"Missing asset: {path}")
        st.stop()
    return base64.b64encode(path.read_bytes()).decode("ascii")


@st.cache_data(show_spinner=False)
def build_html() -> str:
    items = []
    for fn, lbl in PAGES:
        b64 = encode_page(fn)
        stops = STOPS.get(fn, [])
        items.append(
            "{ "
            f'src: "data:image/png;base64,{b64}", '
            f'label: {json.dumps(lbl)}, '
            f"stops: {json.dumps(stops)} "
            "}"
        )
    pages_js = ",\n    ".join(items)
    return HTML_TEMPLATE.replace("__PAGES__", pages_js)


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
<style>
  :root {
    --fg: #eee;
    --shadow: 0 18px 50px rgba(0,0,0,0.65);
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; height: 100%;
    background: radial-gradient(ellipse at center, #1c1c1c 0%, #000 100%);
    color: var(--fg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    overflow: hidden; user-select: none;
    -webkit-touch-callout: none;
  }

  /* === Page mode (full page fits) === */
  .stage {
    position: fixed; inset: 0;
    display: flex; align-items: center; justify-content: center;
    perspective: 2200px;
  }
  .book { position: relative; display: inline-block; line-height: 0; transform-style: preserve-3d; }
  .static-page {
    display: block;
    max-width: calc(100vw - 80px);
    max-height: calc(100vh - 70px);
    border-radius: 4px; box-shadow: var(--shadow); background: #000;
  }
  .flipper {
    position: absolute; inset: 0;
    transform-style: preserve-3d; transform-origin: left center;
    pointer-events: none; visibility: hidden; will-change: transform;
  }
  .flipper.active { visibility: visible; }
  .face {
    position: absolute; inset: 0;
    backface-visibility: hidden; border-radius: 4px; overflow: hidden; background: #000;
  }
  .face img { display: block; width: 100%; height: 100%; object-fit: contain; }
  .face.front { box-shadow: var(--shadow); }
  .face.back {
    transform: rotateY(180deg);
    background: linear-gradient(115deg, #2e2e2e 0%, #161616 100%);
    box-shadow: inset 12px 0 30px rgba(0,0,0,0.55), inset -2px 0 6px rgba(255,255,255,0.05), var(--shadow);
  }
  .face::after {
    content: ""; position: absolute; inset: 0; pointer-events: none;
    opacity: 0; transition: opacity 250ms ease;
  }
  .face.front::after { background: linear-gradient(90deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 35%); }
  .face.back::after  { background: linear-gradient(270deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0) 35%); }
  .flipper.active .face::after { opacity: 1; }
  @keyframes flipForward  { from { transform: rotateY(0deg); }   to { transform: rotateY(-180deg); } }
  @keyframes flipBackward { from { transform: rotateY(-180deg); } to { transform: rotateY(0deg); } }
  .flipper.flip-forward  { animation: flipForward  950ms cubic-bezier(.36,.07,.2,.99) forwards; }
  .flipper.flip-backward { animation: flipBackward 950ms cubic-bezier(.36,.07,.2,.99) forwards; }

  /* === Guided/Read mode: walks predefined stops via scale+translate === */
  .reader {
    position: fixed; inset: 0;
    overflow: hidden;
    background: #000;
    display: none;
    align-items: center;
    justify-content: center;
  }
  body.read-mode .reader { display: flex; }
  body.read-mode .stage  { display: none; }
  .reader-img {
    display: block;
    max-width: 100vw;
    max-height: 100vh;
    transform-origin: center center;
    transition: transform 650ms cubic-bezier(.4, .0, .2, 1);
    will-change: transform;
  }

  /* === UI buttons === */
  .nav {
    position: fixed; top: 50%; transform: translateY(-50%);
    width: 44px; height: 44px; border-radius: 50%;
    background: rgba(255,255,255,0.08); color: var(--fg);
    border: 1px solid rgba(255,255,255,0.15);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; cursor: pointer; backdrop-filter: blur(8px);
    transition: background 200ms, transform 200ms; z-index: 10;
  }
  .nav:hover { background: rgba(255,255,255,0.18); transform: translateY(-50%) scale(1.05); }
  .nav:disabled { opacity: 0.3; cursor: not-allowed; }
  .nav.prev { left: 12px; } .nav.next { right: 12px; }

  .topbar {
    position: fixed; top: 12px; left: 12px;
    display: flex; gap: 8px; z-index: 11;
  }
  .topbar button {
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.20);
    color: var(--fg);
    padding: 10px 18px;
    border-radius: 999px;
    font-size: 14px;
    letter-spacing: 0.04em;
    cursor: pointer;
    backdrop-filter: blur(8px);
  }
  .topbar button:hover { background: rgba(255,255,255,0.20); }

  .hud {
    position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%);
    background: rgba(0,0,0,0.55); padding: 6px 14px; border-radius: 999px;
    font-size: 12px; letter-spacing: 0.05em;
    backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1); z-index: 10;
  }
</style>
</head>
<body>
  <!-- Page mode -->
  <div class="stage" id="stage">
    <div class="book" id="book">
      <img id="static-img" class="static-page" src="" alt="" draggable="false"/>
      <div class="flipper" id="flipper">
        <div class="face front"><img id="front-img" src="" alt="" draggable="false"/></div>
        <div class="face back"></div>
      </div>
    </div>
  </div>

  <!-- Guided / Read mode -->
  <div class="reader" id="reader">
    <img id="reader-img" class="reader-img" src="" alt="" draggable="false"/>
  </div>

  <!-- Controls -->
  <button class="nav prev" id="prev">&#8249;</button>
  <button class="nav next" id="next">&#8250;</button>
  <div class="topbar">
    <button id="toggle">Read mode</button>
  </div>
  <div class="hud" id="hud"></div>

<script>
  const PAGES = [
    __PAGES__
  ];

  const stage      = document.getElementById("stage");
  const reader     = document.getElementById("reader");
  const readerImg  = document.getElementById("reader-img");
  const staticImg  = document.getElementById("static-img");
  const frontImg   = document.getElementById("front-img");
  const flipper    = document.getElementById("flipper");
  const hud        = document.getElementById("hud");
  const prev       = document.getElementById("prev");
  const next       = document.getElementById("next");
  const toggle     = document.getElementById("toggle");

  let current = 0;     // page index
  let stopIdx = 0;     // stop index within current page
  let animating = false;

  // 0 = always start in Read mode; PAGES.length = always Page mode.
  const PAGE_VIEW_LIMIT = 0;

  // === Page mode ===

  const src = (i) => PAGES[i].src;
  function setStatic(idx) { staticImg.src = src(idx); }
  function stopsFor(idx) { return PAGES[idx].stops || []; }

  function flipTo(idx) {
    if (animating) return;
    if (idx < 0 || idx >= PAGES.length || idx === current) return;
    animating = true;
    const forward = idx > current;
    const targetIdx = idx;

    if (forward) {
      frontImg.src = src(current);
      setStatic(targetIdx);
      flipper.classList.add("active", "flip-forward");
    } else {
      frontImg.src = src(targetIdx);
      flipper.classList.add("active", "flip-backward");
    }
    const onEnd = () => {
      flipper.removeEventListener("animationend", onEnd);
      if (!forward) setStatic(targetIdx);
      flipper.classList.remove("active", "flip-forward", "flip-backward");
      current = targetIdx;
      animating = false;
      if (current >= PAGE_VIEW_LIMIT) {
        setReadMode(true);
      }
      updateHud();
    };
    flipper.addEventListener("animationend", onEnd);
  }

  // === Read mode (stops) ===

  function computeStopTransform(stop) {
    const r = readerImg.getBoundingClientRect();
    const dw = r.width, dh = r.height;
    if (dw === 0 || dh === 0) return { tx: 0, ty: 0, s: 1 };
    const vw = window.innerWidth, vh = window.innerHeight;
    // Zoom factor: >1 means stop content overflows the viewport slightly
    // (clipped by .reader overflow:hidden). Tweak to taste.
    const ZOOM = 1.20;
    const s = Math.min(vw / (stop.w * dw), vh / (stop.h * dh)) * ZOOM;
    const cx = (stop.x + stop.w / 2) * dw;
    const cy = (stop.y + stop.h / 2) * dh;
    const tx = -(cx - dw / 2) * s;
    const ty = -(cy - dh / 2) * s;
    return { tx, ty, s };
  }

  function applyStop(smooth) {
    const stops = stopsFor(current);
    if (!stops.length) return;
    const t = computeStopTransform(stops[stopIdx]);
    if (!smooth) readerImg.style.transition = "none";
    else readerImg.style.transition = "";
    readerImg.style.transform =
      `translate3d(${t.tx}px, ${t.ty}px, 0) scale(${t.s})`;
    if (!smooth) {
      // eslint-disable-next-line no-unused-expressions
      readerImg.offsetHeight;
      readerImg.style.transition = "";
    }
  }

  function loadReaderPage(idx, lastStop = false) {
    current = idx;
    readerImg.src = src(idx);
    const finishLoad = () => {
      stopIdx = lastStop ? Math.max(0, stopsFor(idx).length - 1) : 0;
      applyStop(false);
      updateHud();
    };
    if (readerImg.complete && readerImg.naturalWidth) finishLoad();
    else readerImg.onload = finishLoad;
  }

  function readerStep(direction) {
    if (animating) return;
    const stops = stopsFor(current);
    if (direction > 0) {
      if (stopIdx < stops.length - 1) {
        stopIdx += 1;
        applyStop(true);
        updateHud();
      } else if (current < PAGES.length - 1) {
        animating = true;
        loadReaderPage(current + 1, false);
        setTimeout(() => { animating = false; updateHud(); }, 60);
      }
    } else {
      if (stopIdx > 0) {
        stopIdx -= 1;
        applyStop(true);
        updateHud();
      } else if (current > 0) {
        const targetIdx = current - 1;
        if (targetIdx < PAGE_VIEW_LIMIT) {
          // Hand off to page mode and flip back
          setReadMode(false);
          flipTo(targetIdx);
        } else {
          animating = true;
          loadReaderPage(targetIdx, true);
          setTimeout(() => { animating = false; updateHud(); }, 60);
        }
      }
    }
  }

  // === Mode toggle ===

  function isReadMode() { return document.body.classList.contains("read-mode"); }

  function setReadMode(on) {
    if (on) {
      document.body.classList.add("read-mode");
      toggle.textContent = "Page view";
      loadReaderPage(current, false);
    } else {
      document.body.classList.remove("read-mode");
      toggle.textContent = "Read mode";
      setStatic(current);
    }
    updateHud();
  }

  toggle.addEventListener("click", (e) => {
    e.stopPropagation();
    setReadMode(!isReadMode());
  });

  // === HUD ===
  function updateHud() {
    const stops = stopsFor(current);
    const stopInfo = stops.length
      ? `${stopIdx + 1} / ${stops.length}`
      : "";
    const pageInfo = `${PAGES[current].label}  \u00b7  ${current + 1} / ${PAGES.length}`;
    hud.textContent = stopInfo
      ? `${pageInfo}  \u00b7  panel ${stopInfo}`
      : pageInfo;
    if (isReadMode()) {
      prev.disabled = (current === 0 && stopIdx === 0);
      next.disabled = (current === PAGES.length - 1 && stopIdx >= stops.length - 1);
    } else {
      prev.disabled = current === 0;
      next.disabled = current === PAGES.length - 1;
    }
  }

  // === Navigation ===

  function goPrev() { isReadMode() ? readerStep(-1) : flipTo(current - 1); }
  function goNext() { isReadMode() ? readerStep(+1) : flipTo(current + 1); }

  prev.addEventListener("click", (e) => { e.stopPropagation(); goPrev(); });
  next.addEventListener("click", (e) => { e.stopPropagation(); goNext(); });

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft" || e.key === "PageUp") goPrev();
    else if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
      e.preventDefault(); goNext();
    } else if (e.key === "Escape" && isReadMode()) {
      setReadMode(false);
    }
  });

  // Tap to navigate (left half = prev, right half = next)
  function onTap(e) {
    if (e.target.closest(".nav") || e.target.closest(".topbar")) return;
    const x = e.clientX;
    if (x < window.innerWidth / 2) goPrev(); else goNext();
  }
  stage.addEventListener("click", onTap);
  reader.addEventListener("click", onTap);

  // Touch swipe
  let touchX = null, touchY = null;
  document.addEventListener("touchstart", (e) => {
    touchX = e.touches[0].clientX;
    touchY = e.touches[0].clientY;
  }, { passive: true });
  document.addEventListener("touchend", (e) => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    const dy = e.changedTouches[0].clientY - touchY;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) {
      if (dx < 0) goNext(); else goPrev();
    } else if (isReadMode() && Math.abs(dy) > 50 && Math.abs(dy) > Math.abs(dx)) {
      // Vertical swipe also walks stops in Read mode
      readerStep(dy < 0 ? +1 : -1);
    }
    touchX = touchY = null;
  }, { passive: true });

  // Recompute current stop transform on resize
  let resizeT;
  window.addEventListener("resize", () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => {
      if (isReadMode()) applyStop(false);
    }, 120);
  });

  // === Init ===
  if (PAGE_VIEW_LIMIT === 0) {
    setReadMode(true);
  } else {
    setStatic(current);
    updateHud();
  }
</script>
</body>
</html>
"""


# --- Streamlit page ---

st.set_page_config(
    page_title="Comic Book",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 0.5rem; padding-bottom: 0; max-width: 100%; }
      header[data-testid="stHeader"] { background: transparent; }
      footer { display: none; }
      #MainMenu { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(build_html(), height=900, scrolling=False)
