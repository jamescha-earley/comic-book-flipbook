"""Comic book reader with per-page guided view (ComiXology-style).

For each page:
  1. Show the full page.
  2. Smoothly zoom into each panel of that page in sequence.
  3. Flip (3D animation) to the next page's full view, then walk its panels.
  4. Repeat.

PNGs are inlined as base64 so the iframe is self-contained.
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

# Panel rectangles per page, as fractions of the page (x, y, w, h in 0..1).
# Order = reading order (the order panels are walked through during the guided view).
PANELS = {
    "p.2.png": [
        # 4 horizontal stripe panels, full width
        {"x": 0.02, "y": 0.02, "w": 0.96, "h": 0.20},  # Earth
        {"x": 0.02, "y": 0.22, "w": 0.96, "h": 0.22},  # City skyline
        {"x": 0.02, "y": 0.45, "w": 0.96, "h": 0.22},  # Street/people
        {"x": 0.02, "y": 0.66, "w": 0.96, "h": 0.34},  # Blue cyber crowd
    ],
    "p.3-p4.png": [
        # 2-page spread, walk left then right, top then bottom
        {"x": 0.02, "y": 0.02, "w": 0.50, "h": 0.50},  # Top-left intro + photo cluster
        {"x": 0.02, "y": 0.50, "w": 0.50, "h": 0.50},  # Bottom-left title block
        {"x": 0.50, "y": 0.02, "w": 0.50, "h": 0.45},  # Top-right photos
        {"x": 0.50, "y": 0.45, "w": 0.50, "h": 0.55},  # Data Guardians trio
    ],
    "p.5.png": [
        # 2x2 grid of Data Heroes
        {"x": 0.06, "y": 0.02, "w": 0.50, "h": 0.55},  # Datasci (top-left)
        {"x": 0.45, "y": 0.02, "w": 0.55, "h": 0.55},  # Analysta (top-right)
        {"x": 0.05, "y": 0.55, "w": 0.55, "h": 0.45},  # Appdev (bottom-left)
        {"x": 0.40, "y": 0.55, "w": 0.60, "h": 0.45},  # Architecia (bottom-right)
    ],
    "p.6.png": [
        # 3 panels: 2 hero portraits + bottom team scene
        {"x": 0.05, "y": 0.02, "w": 0.55, "h": 0.55},  # The Engineer
        {"x": 0.45, "y": 0.05, "w": 0.55, "h": 0.55},  # Administrator
        {"x": 0.00, "y": 0.55, "w": 1.00, "h": 0.45},  # Full team scene
    ],
    "p.7.png": [
        # 4 panels: villains + heroes + reveal
        {"x": 0.00, "y": 0.00, "w": 1.00, "h": 0.45},  # Silo + intro
        {"x": 0.40, "y": 0.20, "w": 0.60, "h": 0.50},  # Torrent
        {"x": 0.00, "y": 0.40, "w": 0.65, "h": 0.50},  # Dr. Legacy + Data Heroes
        {"x": 0.50, "y": 0.65, "w": 0.50, "h": 0.35},  # Bottom-right villain reveal
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
    pages_js_items = []
    for fn, lbl in PAGES:
        b64 = encode_page(fn)
        panels = PANELS.get(fn, [])
        pages_js_items.append(
            "{ "
            f'src: "data:image/png;base64,{b64}", '
            f'label: {json.dumps(lbl)}, '
            f'file: {json.dumps(fn)}, '
            f"panels: {json.dumps(panels)} "
            "}"
        )
    pages_js = ",\n    ".join(pages_js_items)
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
    --ease: cubic-bezier(.4,.0,.2,1);
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

  /* Viewport clips the page so only what's "in frame" is visible.
     This is what creates the illusion of a camera panning over a fixed comic. */
  .stage {
    position: fixed; inset: 0;
    overflow: hidden;
    display: flex; align-items: center; justify-content: center;
    perspective: 2200px;
  }
  .book {
    position: relative;
    display: inline-block;
    line-height: 0;
    transform-style: preserve-3d;
    transform-origin: center center;
    transition: transform 750ms var(--ease);
    will-change: transform;
  }
  .static-page {
    display: block;
    max-width: calc(100vw - 60px);
    max-height: calc(100vh - 60px);
    border-radius: 4px;
    background: #000;
    box-shadow: var(--shadow);
  }

  /* Flipper covers the natural-size .book area */
  .flipper {
    position: absolute; inset: 0;
    transform-style: preserve-3d;
    transform-origin: left center;
    pointer-events: none;
    visibility: hidden;
    will-change: transform;
    z-index: 5;
  }
  .flipper.active { visibility: visible; }
  .face {
    position: absolute; inset: 0;
    backface-visibility: hidden;
    border-radius: 4px;
    overflow: hidden;
    background: #000;
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
  .flipper.flip-forward  { animation: flipForward  900ms var(--ease) forwards; }
  .flipper.flip-backward { animation: flipBackward 900ms var(--ease) forwards; }

  /* === UI buttons === */
  .nav {
    position: fixed; top: 50%; transform: translateY(-50%);
    width: 44px; height: 44px; border-radius: 50%;
    background: rgba(255,255,255,0.08); color: var(--fg);
    border: 1px solid rgba(255,255,255,0.15);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; cursor: pointer; backdrop-filter: blur(8px);
    transition: background 200ms, transform 200ms; z-index: 20;
  }
  .nav:hover { background: rgba(255,255,255,0.18); transform: translateY(-50%) scale(1.05); }
  .nav:disabled { opacity: 0.3; cursor: not-allowed; }
  .nav.prev { left: 12px; } .nav.next { right: 12px; }

  .hud {
    position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%);
    background: rgba(0,0,0,0.55); padding: 6px 14px; border-radius: 999px;
    font-size: 12px; letter-spacing: 0.05em;
    backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1); z-index: 20;
  }
</style>
</head>
<body>
  <div class="stage" id="stage">
    <div class="book" id="book">
      <img id="static-img" class="static-page" src="" alt="" draggable="false"/>
      <div class="flipper" id="flipper">
        <div class="face front"><img id="front-img" src="" alt="" draggable="false"/></div>
        <div class="face back"></div>
      </div>
    </div>
  </div>

  <button class="nav prev" id="prev" aria-label="Previous">&#8249;</button>
  <button class="nav next" id="next" aria-label="Next">&#8250;</button>
  <div class="hud" id="hud"></div>

<script>
  const PAGES = [
    __PAGES__
  ];

  // Build the linear list of "steps" the user walks through.
  // Each step = { pageIdx, panelIdx } where panelIdx === -1 means full page.
  const STEPS = [];
  PAGES.forEach((p, pageIdx) => {
    STEPS.push({ pageIdx, panelIdx: -1 });
    p.panels.forEach((_, panelIdx) => {
      STEPS.push({ pageIdx, panelIdx });
    });
  });

  const stage     = document.getElementById("stage");
  const book      = document.getElementById("book");
  const staticImg = document.getElementById("static-img");
  const frontImg  = document.getElementById("front-img");
  const flipper   = document.getElementById("flipper");
  const hud       = document.getElementById("hud");
  const prevBtn   = document.getElementById("prev");
  const nextBtn   = document.getElementById("next");

  let stepIdx = 0;
  let animating = false;

  // Per-page uniform panel scale: same scale for every panel on a given page,
  // so that panel-to-panel transitions are pure translate (true camera pan).
  // Computed lazily once the page image has laid out.
  const pagePanelScale = new Array(PAGES.length).fill(null);

  const src = (i) => PAGES[i].src;
  function setStatic(idx) { staticImg.src = src(idx); }

  function panelFor(step) {
    if (step.panelIdx === -1) return null;
    return PAGES[step.pageIdx].panels[step.panelIdx] || null;
  }

  function imgRect() { return staticImg.getBoundingClientRect(); }

  function computePagePanelScale(pageIdx) {
    const r = imgRect();
    const dw = r.width, dh = r.height;
    if (dw === 0 || dh === 0) return 1;
    const vw = window.innerWidth, vh = window.innerHeight;
    const panels = PAGES[pageIdx].panels;
    if (!panels.length) return 1;
    // For each panel, find the scale needed to fit it into ~94% of viewport.
    // Use the MINIMUM across panels so every panel fits with the same scale.
    let s = Infinity;
    for (const p of panels) {
      const fit = Math.min(vw / (p.w * dw), vh / (p.h * dh)) * 0.94;
      s = Math.min(s, fit);
    }
    return Math.max(1, s);  // never zoom out below natural fit
  }

  function getPanelScale(pageIdx) {
    if (pagePanelScale[pageIdx] == null) {
      pagePanelScale[pageIdx] = computePagePanelScale(pageIdx);
    }
    return pagePanelScale[pageIdx];
  }

  function transformForStep(step) {
    if (step.panelIdx === -1) {
      // Full page = natural fit, no transform
      return { tx: 0, ty: 0, s: 1 };
    }
    const panel = panelFor(step);
    const s = getPanelScale(step.pageIdx);
    const r = imgRect();
    const dw = r.width, dh = r.height;
    const cx = (panel.x + panel.w / 2) * dw;
    const cy = (panel.y + panel.h / 2) * dh;
    // Translate (in screen pixels) so panel center lands at viewport center.
    const tx = -(cx - dw / 2) * s;
    const ty = -(cy - dh / 2) * s;
    return { tx, ty, s };
  }

  function applyTransform(t, smooth) {
    if (!smooth) book.style.transition = "none";
    else book.style.transition = "";
    book.style.transform =
      `translate3d(${t.tx}px, ${t.ty}px, 0) scale(${t.s})`;
    if (!smooth) {
      // eslint-disable-next-line no-unused-expressions
      book.offsetHeight;
      book.style.transition = "";
    }
  }

  function applyStepTransform(step, smooth) {
    applyTransform(transformForStep(step), smooth);
  }

  function gotoStep(newIdx) {
    if (animating) return;
    if (newIdx < 0 || newIdx >= STEPS.length) return;
    if (newIdx === stepIdx) return;
    const oldStep = STEPS[stepIdx];
    const newStep = STEPS[newIdx];

    if (oldStep.pageIdx === newStep.pageIdx) {
      // Same page: smooth transition. Panel-to-panel is translate-only at the
      // same scale (camera pan); full<->panel involves a scale change too.
      stepIdx = newIdx;
      applyStepTransform(newStep, true);
      updateHud();
      return;
    }

    // Page change: snap zoom to identity then run 3D flip
    animating = true;
    applyTransform({ tx: 0, ty: 0, s: 1 }, false);
    const forward = newStep.pageIdx > oldStep.pageIdx;

    if (forward) {
      frontImg.src = src(oldStep.pageIdx);
      setStatic(newStep.pageIdx);
      flipper.classList.add("active", "flip-forward");
    } else {
      frontImg.src = src(newStep.pageIdx);
      flipper.classList.add("active", "flip-backward");
    }

    const onEnd = () => {
      flipper.removeEventListener("animationend", onEnd);
      if (!forward) setStatic(newStep.pageIdx);
      flipper.classList.remove("active", "flip-forward", "flip-backward");
      stepIdx = newIdx;
      animating = false;
      // Recompute panel scale for the new page (image dims may differ)
      pagePanelScale[newStep.pageIdx] = null;
      // After landing on new page, if target step is a panel, smoothly camera-pan in
      if (newStep.panelIdx !== -1) {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => applyStepTransform(newStep, true));
        });
      }
      updateHud();
    };
    flipper.addEventListener("animationend", onEnd);
  }

  function goPrev() { gotoStep(stepIdx - 1); }
  function goNext() { gotoStep(stepIdx + 1); }

  // === HUD ===
  function updateHud() {
    const step = STEPS[stepIdx];
    const page = PAGES[step.pageIdx];
    const panelInfo = step.panelIdx === -1
      ? "full page"
      : `panel ${step.panelIdx + 1} / ${page.panels.length}`;
    hud.textContent = `${page.label}  ·  ${panelInfo}  ·  ${step.pageIdx + 1} / ${PAGES.length}`;
    prevBtn.disabled = stepIdx === 0;
    nextBtn.disabled = stepIdx === STEPS.length - 1;
  }

  // === Input ===
  prevBtn.addEventListener("click", (e) => { e.stopPropagation(); goPrev(); });
  nextBtn.addEventListener("click", (e) => { e.stopPropagation(); goNext(); });

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft" || e.key === "PageUp") {
      e.preventDefault(); goPrev();
    } else if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
      e.preventDefault(); goNext();
    }
  });

  // Tap to navigate (left half = prev, right half = next)
  function onTap(e) {
    if (e.target.closest(".nav")) return;
    const x = e.clientX;
    if (x < window.innerWidth / 2) goPrev(); else goNext();
  }
  stage.addEventListener("click", onTap);

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
    }
    touchX = touchY = null;
  }, { passive: true });

  // Recompute current transform on resize so the panel zoom stays correct
  let resizeT;
  window.addEventListener("resize", () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => {
      // Invalidate all per-page cached scales (they depend on viewport size)
      for (let i = 0; i < pagePanelScale.length; i++) pagePanelScale[i] = null;
      const step = STEPS[stepIdx];
      if (step.panelIdx !== -1) applyStepTransform(step, false);
    }, 120);
  });

  // === Init ===
  function init() {
    setStatic(0);
    // Wait for the first image to load so transforms compute correctly
    if (staticImg.complete) {
      updateHud();
    } else {
      staticImg.addEventListener("load", updateHud, { once: true });
    }
  }
  init();
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
