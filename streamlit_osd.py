"""OpenSeadragon-based guided-view comic reader (ComiXology-style panel navigation).

Uses OpenSeadragon to display comic pages and animates viewport.fitBounds()
between predefined panel rectangles for a guided reading experience.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# --- Page definitions with panel rectangles (fractional coords: x, y, w, h in 0..1) ---

PAGES = [
    ("p.2.png", "p. 2"),
    ("p.3-p4.png", "p. 3-4"),
    ("p.5.png", "p. 5"),
    ("p.6.png", "p. 6"),
    ("p.7.png", "p. 7"),
]

PANELS = {
    "p.2.png": [
        {"x": 0.02, "y": 0.02, "w": 0.96, "h": 0.21},
        {"x": 0.02, "y": 0.23, "w": 0.96, "h": 0.22},
        {"x": 0.02, "y": 0.45, "w": 0.96, "h": 0.22},
        {"x": 0.02, "y": 0.66, "w": 0.96, "h": 0.34},
    ],
    "p.3-p4.png": [
        {"x": 0.00, "y": 0.00, "w": 0.50, "h": 0.50},
        {"x": 0.50, "y": 0.00, "w": 0.50, "h": 0.50},
        {"x": 0.00, "y": 0.50, "w": 0.50, "h": 0.50},
        {"x": 0.50, "y": 0.50, "w": 0.50, "h": 0.50},
    ],
    "p.5.png": [
        {"x": 0.06, "y": 0.02, "w": 0.50, "h": 0.55},
        {"x": 0.45, "y": 0.02, "w": 0.55, "h": 0.55},
        {"x": 0.05, "y": 0.55, "w": 0.55, "h": 0.45},
        {"x": 0.40, "y": 0.55, "w": 0.60, "h": 0.45},
    ],
    "p.6.png": [
        {"x": 0.05, "y": 0.02, "w": 0.55, "h": 0.55},
        {"x": 0.45, "y": 0.05, "w": 0.55, "h": 0.55},
        {"x": 0.00, "y": 0.55, "w": 1.00, "h": 0.45},
    ],
    "p.7.png": [
        {"x": 0.00, "y": 0.00, "w": 1.00, "h": 0.45},
        {"x": 0.40, "y": 0.20, "w": 0.60, "h": 0.50},
        {"x": 0.00, "y": 0.40, "w": 0.65, "h": 0.50},
        {"x": 0.50, "y": 0.65, "w": 0.50, "h": 0.35},
    ],
}

ASSET_DIR = Path(__file__).parent


def encode_page(filename: str) -> str:
    path = ASSET_DIR / filename
    if not path.exists():
        st.error(f"Missing asset: {path}")
        st.stop()
    return base64.b64encode(path.read_bytes()).decode("ascii")


def get_image_dimensions(filename: str) -> tuple[int, int]:
    """Read PNG dimensions from the IHDR chunk (bytes 16-24)."""
    path = ASSET_DIR / filename
    data = path.read_bytes()
    # PNG IHDR: width at offset 16 (4 bytes BE), height at offset 20 (4 bytes BE)
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


@st.cache_data(show_spinner=False)
def build_html() -> str:
    # Build pages data with base64 sources, labels, panels, and explicit dims
    pages_data = []
    for fn, lbl in PAGES:
        w, h = get_image_dimensions(fn)
        b64 = encode_page(fn)
        panels = PANELS.get(fn, [{"x": 0, "y": 0, "w": 1, "h": 1}])
        pages_data.append({
            "src": f"data:image/png;base64,{b64}",
            "label": lbl,
            "width": w,
            "height": h,
            "aspect": h / w,
            "panels": panels,
        })

    pages_json = json.dumps(pages_data)
    return HTML_TEMPLATE.replace("__PAGES_JSON__", pages_json)


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    height: 100%; overflow: hidden;
    background: #0a0a0a; color: #eee;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    user-select: none;
  }
  #viewer {
    width: 100%; height: 100%;
    background: #0a0a0a;
  }
  .hud {
    position: fixed; bottom: 14px; left: 50%; transform: translateX(-50%);
    background: rgba(0,0,0,0.7); padding: 8px 18px; border-radius: 999px;
    font-size: 13px; letter-spacing: 0.04em; white-space: nowrap;
    backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.12);
    z-index: 100; pointer-events: none;
  }
  .nav-zone {
    position: fixed; top: 0; bottom: 0; width: 30%; z-index: 50; cursor: pointer;
  }
  .nav-zone.left { left: 0; }
  .nav-zone.right { right: 0; }
  .nav-zone:hover { background: rgba(255,255,255,0.02); }
  .nav-hint {
    position: fixed; top: 50%; transform: translateY(-50%);
    width: 40px; height: 40px; border-radius: 50%;
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; z-index: 60; opacity: 0; transition: opacity 200ms;
    pointer-events: none;
  }
  .nav-zone:hover + .nav-hint, .nav-hint:hover { opacity: 1; }
  .nav-hint.left { left: 14px; }
  .nav-hint.right { right: 14px; }
  .instructions {
    position: fixed; top: 14px; left: 50%; transform: translateX(-50%);
    background: rgba(0,0,0,0.7); padding: 8px 16px; border-radius: 8px;
    font-size: 12px; opacity: 0.8; z-index: 100; pointer-events: none;
    backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1);
    transition: opacity 1.5s ease;
  }
</style>
</head>
<body>
  <div id="viewer"></div>
  <div class="nav-zone left" id="nav-left"></div>
  <div class="nav-hint left">&#8249;</div>
  <div class="nav-zone right" id="nav-right"></div>
  <div class="nav-hint right">&#8250;</div>
  <div class="hud" id="hud">Loading…</div>
  <div id="logbox" style="position:fixed;top:8px;right:8px;max-width:60%;max-height:50%;overflow:auto;background:rgba(0,0,0,.75);color:#9cf;font:11px/1.3 monospace;padding:6px 8px;border-radius:6px;z-index:200;display:none;"></div>
  <div class="instructions" id="instructions">Tap right / left or use arrow keys to navigate panels</div>

<script src="https://cdn.jsdelivr.net/npm/openseadragon@5.0/build/openseadragon/openseadragon.min.js"></script>
<script>
(function() {
  const PAGES = __PAGES_JSON__;

  let currentPage = 0;
  let currentPanel = -1; // -1 means "full page view" before first panel
  let viewer = null;

  const hud = document.getElementById('hud');
  const instructions = document.getElementById('instructions');
  const logbox = document.getElementById('logbox');

  function log(msg) {
    console.log('[osd]', msg);
    if (logbox) {
      logbox.style.display = 'block';
      const line = document.createElement('div');
      line.textContent = msg;
      logbox.appendChild(line);
      logbox.scrollTop = logbox.scrollHeight;
    }
  }
  window.addEventListener('error', function(e) { log('JS error: ' + e.message); });

  // Fade out instructions after 4 seconds
  setTimeout(() => { instructions.style.opacity = '0'; }, 4000);

  function updateHud() {
    const page = PAGES[currentPage];
    const totalPanels = page.panels.length;
    if (currentPanel < 0) {
      hud.textContent = `${page.label} · overview`;
    } else {
      hud.textContent = `${page.label} · panel ${currentPanel + 1} / ${totalPanels}`;
    }
  }

  function getPanelBounds(pageIdx, panelIdx) {
    const page = PAGES[pageIdx];
    const panel = page.panels[panelIdx];
    const aspect = page.aspect; // height/width ratio

    // OSD viewport coords: x is in [0..1] for image width,
    // y is in [0..aspect] for image height.
    // Panel fractional coords are relative to image dimensions:
    //   panel.x, panel.w are fractions of image width -> use directly
    //   panel.y, panel.h are fractions of image height -> multiply by aspect
    return new OpenSeadragon.Rect(
      panel.x,
      panel.y * aspect,
      panel.w,
      panel.h * aspect
    );
  }

  function getFullPageBounds(pageIdx) {
    const aspect = PAGES[pageIdx].aspect;
    return new OpenSeadragon.Rect(0, 0, 1, aspect);
  }

  function pageTileSource(pageIdx) {
    // Custom "single-image" tile source with explicit dims — skips OSD's
    // image-load step which is slow with multi-MB base64 data URLs.
    const p = PAGES[pageIdx];
    return {
      width: p.width,
      height: p.height,
      tileSize: Math.max(p.width, p.height),
      minLevel: 0,
      maxLevel: 0,
      getTileUrl: function() { return p.src; },
    };
  }

  function initViewer() {
    log('Initializing OpenSeadragon viewer...');
    if (typeof OpenSeadragon === 'undefined') {
      log('ERROR: OpenSeadragon library failed to load from CDN');
      return;
    }
    try {
      viewer = OpenSeadragon({
        id: 'viewer',
        prefixUrl: 'https://cdn.jsdelivr.net/npm/openseadragon@5.0/build/openseadragon/images/',
        tileSources: pageTileSource(currentPage),
        showNavigationControl: false,
        showNavigator: false,
        animationTime: 0.6,
        springStiffness: 8,
        visibilityRatio: 0.5,
        minZoomLevel: 0.5,
        maxZoomLevel: 10,
        gestureSettingsMouse: {
          scrollToZoom: false, clickToZoom: false, dblClickToZoom: false, flickEnabled: false,
        },
        gestureSettingsTouch: {
          scrollToZoom: false, clickToZoom: false, dblClickToZoom: false, pinchToZoom: true, flickEnabled: false,
        },
        gestureSettingsPen: {
          scrollToZoom: false, clickToZoom: false, dblClickToZoom: false,
        },
        defaultZoomLevel: 0,
        immediateRender: true,
      });

      viewer.addHandler('open', function() {
        log('Page open. Fitting full page first.');
        viewer.viewport.fitBounds(getFullPageBounds(currentPage), true);
        updateHud();
      });
      viewer.addHandler('open-failed', function(e) {
        log('open-failed: ' + (e && e.message ? e.message : JSON.stringify(e)));
      });
      viewer.addHandler('tile-load-failed', function(e) {
        log('tile-load-failed: ' + (e && e.message ? e.message : 'unknown'));
      });
    } catch (err) {
      log('Init error: ' + err.message);
    }
  }

  function openPage(pageIdx, startPanel) {
    currentPage = pageIdx;
    currentPanel = startPanel;
    viewer.open(pageTileSource(pageIdx));
    viewer.addOnceHandler('open', function() {
      if (currentPanel >= 0) {
        viewer.viewport.fitBounds(getPanelBounds(currentPage, currentPanel), false);
      } else {
        viewer.viewport.fitBounds(getFullPageBounds(currentPage), true);
      }
      updateHud();
    });
  }

  function goNext() {
    const page = PAGES[currentPage];
    const totalPanels = page.panels.length;

    if (currentPanel < totalPanels - 1) {
      // Next panel on same page
      currentPanel++;
      viewer.viewport.fitBounds(getPanelBounds(currentPage, currentPanel), false);
      updateHud();
    } else if (currentPage < PAGES.length - 1) {
      // Advance to next page, first panel
      openPage(currentPage + 1, 0);
    }
    // else: at last panel of last page, do nothing
  }

  function goPrev() {
    if (currentPanel > 0) {
      // Previous panel on same page
      currentPanel--;
      viewer.viewport.fitBounds(getPanelBounds(currentPage, currentPanel), false);
      updateHud();
    } else if (currentPanel === 0 && currentPage > 0) {
      // Go to previous page, last panel
      const prevPage = currentPage - 1;
      const lastPanel = PAGES[prevPage].panels.length - 1;
      openPage(prevPage, lastPanel);
    }
    // else: at first panel of first page, do nothing
  }

  // Navigation handlers
  document.getElementById('nav-right').addEventListener('click', goNext);
  document.getElementById('nav-left').addEventListener('click', goPrev);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowRight' || e.key === ' ') {
      e.preventDefault();
      goNext();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      goPrev();
    }
  });

  // Touch swipe support
  let touchStartX = 0;
  document.addEventListener('touchstart', function(e) {
    touchStartX = e.changedTouches[0].clientX;
  }, { passive: true });
  document.addEventListener('touchend', function(e) {
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) {
      if (dx < 0) goNext();
      else goPrev();
    }
  }, { passive: true });

  // Initialize
  initViewer();
  // Start at first panel after a brief moment showing full page
  setTimeout(function() {
    currentPanel = 0;
    viewer.viewport.fitBounds(getPanelBounds(currentPage, currentPanel), false);
    updateHud();
  }, 800);
})();
</script>
</body>
</html>
"""


# --- Streamlit page ---

st.set_page_config(
    page_title="Comic - Guided View",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 0; padding-bottom: 0; max-width: 100%; }
      header[data-testid="stHeader"] { background: transparent; }
      footer { display: none; }
      #MainMenu { visibility: hidden; }
      iframe { border: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(build_html(), height=720, scrolling=False)
