"""Comic book flipbook embedded in a Streamlit app via st.components.v1.html.

Inlines the PNGs as base64 data URLs so the iframe is fully self-contained.
"""

from __future__ import annotations

import base64
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

ASSET_DIR = Path(__file__).parent


def encode_page(filename: str) -> str:
    path = ASSET_DIR / filename
    if not path.exists():
        st.error(f"Missing asset: {path}")
        st.stop()
    return base64.b64encode(path.read_bytes()).decode("ascii")


@st.cache_data(show_spinner=False)
def build_html() -> str:
    pages_js = ",\n    ".join(
        f'{{ src: "data:image/png;base64,{encode_page(fn)}", label: "{lbl}" }}'
        for fn, lbl in PAGES
    )
    return HTML_TEMPLATE.replace("__PAGES__", pages_js)


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
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
  }
  .stage {
    position: fixed; inset: 0;
    display: flex; align-items: center; justify-content: center;
    perspective: 2200px;
  }
  .book { position: relative; display: inline-block; line-height: 0; transform-style: preserve-3d; }
  .static-page {
    display: block;
    max-width: calc(100vw - 120px);
    max-height: calc(100vh - 60px);
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
  .hud {
    position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%);
    background: rgba(0,0,0,0.55); padding: 6px 14px; border-radius: 999px;
    font-size: 12px; letter-spacing: 0.05em;
    backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1); z-index: 10;
  }
</style>
</head>
<body>
  <div class="stage">
    <div class="book" id="book">
      <img id="static-img" class="static-page" src="" alt="" draggable="false"/>
      <div class="flipper" id="flipper">
        <div class="face front"><img id="front-img" src="" alt="" draggable="false"/></div>
        <div class="face back"></div>
      </div>
    </div>
  </div>
  <button class="nav prev" id="prev">&#8249;</button>
  <button class="nav next" id="next">&#8250;</button>
  <div class="hud" id="hud"></div>

<script>
  const PAGES = [
    __PAGES__
  ];
  const staticImg = document.getElementById("static-img");
  const frontImg  = document.getElementById("front-img");
  const flipper   = document.getElementById("flipper");
  const hud       = document.getElementById("hud");
  const prev      = document.getElementById("prev");
  const next      = document.getElementById("next");

  let current = 0;
  let animating = false;

  const src = (i) => PAGES[i].src;
  function updateHud() {
    hud.textContent = `${PAGES[current].label}  ·  ${current + 1} / ${PAGES.length}`;
    prev.disabled = current === 0;
    next.disabled = current === PAGES.length - 1;
  }
  function setStatic(idx) { staticImg.src = src(idx); }

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
      updateHud();
    };
    flipper.addEventListener("animationend", onEnd);
  }

  prev.addEventListener("click", (e) => { e.stopPropagation(); flipTo(current - 1); });
  next.addEventListener("click", (e) => { e.stopPropagation(); flipTo(current + 1); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") flipTo(current - 1);
    else if (e.key === "ArrowRight" || e.key === " ") { e.preventDefault(); flipTo(current + 1); }
  });
  document.querySelector(".stage").addEventListener("click", (e) => {
    if (e.target.closest(".nav")) return;
    const rect = document.querySelector(".stage").getBoundingClientRect();
    const x = e.clientX - rect.left;
    flipTo(current + (x < rect.width / 2 ? -1 : 1));
  });

  setStatic(current);
  updateHud();
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
