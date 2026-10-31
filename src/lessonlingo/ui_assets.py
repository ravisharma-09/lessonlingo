"""Look and feel of the web UI: slim pixel header, step bar and one set of spacing rules."""

from __future__ import annotations

HERO_HTML = """
<div id="topbar">
  <svg viewBox="0 0 56 48" width="50" height="43" class="logo" role="img" aria-label="LessonLingo logo">
  <path d="M6 2h28a6 6 0 0 1 6 6v14a6 6 0 0 1-6 6H19l-8 7v-7H6a6 6 0 0 1-6-6V8a6 6 0 0 1 6-6z" fill="var(--ll-accent)"/>
  <text x="20" y="21" text-anchor="middle" font-size="18" font-weight="800" fill="#ffffff" font-family="Figtree, Arial, sans-serif">A</text>
  <path d="M31 19h19a6 6 0 0 1 6 6v10a6 6 0 0 1-6 6h-1v6l-7-6H31a6 6 0 0 1-6-6V25a6 6 0 0 1 6-6z" fill="var(--ll-surface)" stroke="var(--ll-accent)" stroke-width="2.5"/>
  <text x="40.5" y="37" text-anchor="middle" font-size="17" font-weight="700" fill="var(--ll-accent)" font-family="Noto Sans Devanagari, Arial, sans-serif">अ</text>
</svg>
  <b>Lesson<span>Lingo</span></b>
  <span class="tag">Translate lectures and lessons. Works offline.</span>
  <div class="palette" role="group" aria-label="Colour palette"><button type="button" class="sw" data-palette="tide" title="Tide" aria-label="Tide palette" style="background:#0b6e69" onclick="llPalette('tide')"></button><button type="button" class="sw" data-palette="forest" title="Forest" aria-label="Forest palette" style="background:#2f7d3a" onclick="llPalette('forest')"></button><button type="button" class="sw" data-palette="ocean" title="Ocean" aria-label="Ocean palette" style="background:#1d4ed8" onclick="llPalette('ocean')"></button><button type="button" class="sw" data-palette="plum" title="Plum" aria-label="Plum palette" style="background:#7c3aed" onclick="llPalette('plum')"></button><button type="button" class="sw" data-palette="sunset" title="Sunset" aria-label="Sunset palette" style="background:#c2410c" onclick="llPalette('sunset')"></button></div>
</div>
"""

FORCE_LIGHT_JS = """() => {
  const light = () => document.body.classList.remove('dark');
  light();
  new MutationObserver(light).observe(document.body, {
    attributes: true,
    attributeFilter: ['class'],
  });
  const read = () => {
    try { return localStorage.getItem('ll-palette') || 'tide'; } catch (e) { return 'tide'; }
  };
  const paint = (name) => {
    document.body.dataset.palette = name;
    document.querySelectorAll('#topbar .sw').forEach((b) => {
      b.classList.toggle('on', b.dataset.palette === name);
    });
  };
  window.llPalette = (name) => {
    try { localStorage.setItem('ll-palette', name); } catch (e) { /* private window */ }
    paint(name);
  };
  paint(read());
  setTimeout(() => paint(read()), 600);
  setTimeout(() => paint(read()), 1800);
}"""

SCROLL_TOP_JS = "() => { window.scrollTo({ top: 0, behavior: 'smooth' }); }"

STYLE_CSS = """
@import url("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&display=swap");
/* One theme: paper page, dark menu panel, one teal accent. */
:root, body {
  --ll-accent: #0b6e69; --ll-accent-hi: #12a58e; --ll-accent-ink: #ffffff;
  --ll-soft: #e3efed; --ll-soft-text: #08524e; --ll-surface: #ffffff; --ll-page: #f1f4f3;
  --ll-border: #dce3e1; --ll-line: #dce3e1; --ll-text: #121a19; --ll-muted: #4f5957;
  --ll-off: #8a9896; --ll-night: #0e1414; --ll-night-text: #a9aeb8;
  --ll-display: "Bricolage Grotesque", "Avenir Next", Figtree, system-ui, sans-serif;
}
body[data-palette="forest"] { --ll-accent: #2f7d3a; --ll-accent-hi: #4fb35e; --ll-soft: #e5f1e6;
  --ll-soft-text: #1f5a28; --ll-night: #101810; --ll-page: #f2f5f1; --ll-border: #dae4d9; }
body[data-palette="ocean"] { --ll-accent: #1d4ed8; --ll-accent-hi: #3b82f6; --ll-soft: #e5ecfb;
  --ll-soft-text: #1e3a8a; --ll-night: #0d1220; --ll-page: #f1f3f8; --ll-border: #dae0ee; }
body[data-palette="plum"] { --ll-accent: #7c3aed; --ll-accent-hi: #a78bfa; --ll-soft: #eee8fb;
  --ll-soft-text: #4c1d95; --ll-night: #140f1f; --ll-page: #f4f2f8; --ll-border: #e2dcee; }
body[data-palette="sunset"] { --ll-accent: #c2410c; --ll-accent-hi: #f97316; --ll-soft: #fbebe0;
  --ll-soft-text: #7c2d12; --ll-night: #1a1210; --ll-page: #f8f4f1; --ll-border: #ecdfd6; }
body, .gradio-container { background: var(--ll-page) !important; color: var(--ll-text); }

/* Page shell: full width, teal band on top, menu on the left, page on the right. */
.gradio-container { max-width: 1760px !important; margin: 0 auto !important;
  padding: 0 28px 40px !important; font-size: 17px; }
.html-container { padding: 0 !important; }
footer { display: none !important; }
.form { background: transparent !important; border: 0 !important; box-shadow: none !important;
  gap: 18px !important; }
span[data-testid="block-info"], .block label > span { color: var(--ll-muted) !important;
  font-weight: 700; }
.block:has(button.upload-container) { height: auto !important; }
fieldset.block { padding: 0 !important; border: 0 !important; background: transparent !important; }

#topbar { display: flex; align-items: center; gap: 12px; margin: 0 0 18px; padding: 18px 4px 6px; }
#topbar .logo { flex: none; transition: transform .2s; }
#topbar:hover .logo { transform: rotate(-4deg) scale(1.05); }
#topbar b span { color: var(--ll-accent); }
#topbar .mark-unused { width: 36px; height: 36px; border-radius: 10px; background: var(--ll-accent);
  color: #fff !important; display: grid; place-items: center; font-weight: 900; font-size: 1.2rem; }
#topbar b { font-family: var(--ll-display); font-size: 1.5rem; letter-spacing: -.02em; color: var(--ll-text) !important; }
#topbar .palette { display: flex; gap: 8px; align-items: center; }
#topbar .sw { width: 22px; height: 22px; border-radius: 50%; border: 3px solid var(--ll-surface);
  box-shadow: 0 0 0 1.5px var(--ll-border); cursor: pointer; padding: 0; }
#topbar .sw.on { box-shadow: 0 0 0 2px var(--ll-text); }
#topbar .tag { color: var(--ll-muted) !important; font-size: .95rem; margin-left: auto; margin-right: 8px; }

#shell.tabs { display: grid !important; grid-template-columns: 290px minmax(0, 1fr); gap: 32px;
  align-items: start; }
#shell > .tab-wrapper { grid-column: 1; position: sticky; top: 16px; height: auto !important;
  background: var(--ll-night); border: 0; border-radius: 22px;
  padding: 14px; }
#shell > .tab-wrapper .tab-container { flex-direction: column !important; height: auto !important;
  gap: 4px; align-items: stretch; }
#shell > .tab-wrapper .tab-container::after { display: none !important; }
#shell > .tab-wrapper .tab-container.visually-hidden { display: none !important; }
/* Gradio adds a second copy of the last tab once its page has loaded; show six only. */
#shell > .tab-wrapper .tab-container button[role="tab"]:nth-child(n + 7) {
  display: none !important; }
#shell > .tab-wrapper .overflow-menu { display: none !important; }
#shell > .tab-wrapper button[role="tab"] { text-align: left; justify-content: flex-start;
  padding: 14px 16px !important; border-radius: 12px !important; border: 0 !important;
  font-size: 1.02rem; font-weight: 600; color: var(--ll-night-text) !important;
  background: transparent !important; height: auto !important; border-radius: 999px !important; }
#shell > .tab-wrapper button[role="tab"]:hover { background: rgba(255, 255, 255, 0.08) !important; }
#shell > .tab-wrapper button[role="tab"].selected::after { display: none !important; }
#shell > .tab-wrapper button[role="tab"].selected { background: var(--ll-accent) !important;
  color: #ffffff !important; font-weight: 800; }
#shell > .tab-wrapper button[role="tab"]:disabled { opacity: .45; cursor: not-allowed; }
#shell > .tab-wrapper button[role="tab"]:nth-child(6) { margin-top: 14px; position: relative; }
#shell > .tabitem { grid-column: 2; padding: 0 !important; border: 0 !important; }

.page { gap: 20px !important; padding-bottom: 12px; }
.page-head h2 { font-family: var(--ll-display); font-size: 2.8rem; font-weight: 800;
  letter-spacing: -0.03em; line-height: 1.02; margin: 0 0 8px; color: var(--ll-text); }
.page-head p { margin: 0; color: var(--ll-muted); font-size: 1rem; }
.hint, .hint p { color: var(--ll-muted) !important; font-size: 0.98rem; }
.split { gap: 28px !important; align-items: flex-start !important; }
.split > * { min-width: 0; }
.side-card { background: var(--ll-surface); border: 1px solid var(--ll-border);
  border-radius: 22px; padding: 22px !important; gap: 18px !important; }
.side-card h3 { margin-top: 0; }
.nav-bar { position: sticky; bottom: 0; z-index: 5; background: var(--ll-page);
  border-top: 1px solid var(--ll-border); padding: 14px 0 !important; gap: 12px !important;
  justify-content: flex-end; }
.nav-bar > * { flex: 0 1 auto !important; min-width: 200px; }

/* Folded sections */
.label-wrap { width: 100%; display: flex !important; justify-content: space-between;
  align-items: center; padding: 14px 18px !important; border: 1px solid var(--ll-border) !important;
  border-radius: 999px !important; background: var(--ll-surface) !important;
  color: var(--ll-text) !important; font-size: 1.02rem; font-weight: 700; cursor: pointer; }
.label-wrap:hover { border-color: var(--ll-accent) !important; }
.label-wrap:focus-visible, button:focus-visible { outline: 2px solid var(--ll-accent);
  outline-offset: 2px; }
.label-wrap .icon { color: var(--ll-accent) !important; }
.label-wrap + div { padding: 16px 4px 4px; }

/* Drop area */
button.upload-container { min-height: 160px; padding: 44px 16px 20px !important;
  border: 2px dashed var(--ll-accent) !important;
  background: var(--ll-soft) !important; border-radius: 16px !important;
  color: var(--ll-soft-text) !important; }
button.upload-container * { color: var(--ll-soft-text) !important; }

/* Choice tiles: big, with a visible selected state. */
[data-testid="checkbox-group"] { display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
[data-testid="checkbox-group"] label, label[data-testid$="-radio-label"] {
  display: flex !important; align-items: center; gap: 10px; min-height: 54px;
  padding: 12px 16px !important; font-size: 1.02rem; cursor: pointer;
  border-radius: 16px !important; border: 1.5px solid var(--ll-border) !important;
  background: var(--ll-surface) !important; box-shadow: none !important;
  color: var(--ll-text) !important; }
[data-testid="checkbox-group"] label:hover, label[data-testid$="-radio-label"]:hover {
  border-color: var(--ll-accent) !important; }
[data-testid="checkbox-group"] label.selected, label[data-testid$="-radio-label"].selected {
  border-color: var(--ll-accent) !important; background: var(--ll-accent) !important;
  color: #ffffff !important; font-weight: 700; }
[data-testid="checkbox-group"] label.selected::after,
label[data-testid$="-radio-label"].selected::after {
  content: "\\2713"; margin-left: auto; color: #ffffff; font-weight: 800; }
[data-testid="checkbox-group"] input, label[data-testid$="-radio-label"] input {
  position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
[data-testid="checkbox-group"] label span,
label[data-testid$="-radio-label"] span { margin: 0 !important; color: inherit !important;
  font-weight: inherit !important; }
div:has(> label[data-testid$="-radio-label"]) { display: grid !important; gap: 10px; }
.lang-chips div:has(> label[data-testid$="-radio-label"]) {
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }

/* Buttons */
button.primary, .primary { min-height: 54px; font-size: 1.08rem !important; font-weight: 800 !important;
  border-radius: 999px !important; background: var(--ll-accent) !important;
  color: var(--ll-accent-ink) !important; border: 0 !important; }
button.secondary { min-height: 54px; font-size: 1.05rem !important; font-weight: 700 !important;
  border-radius: 999px !important; background: var(--ll-surface) !important;
  color: var(--ll-text) !important; border: 1px solid var(--ll-border) !important; }
.link-button, .link-button button, button.link-button { min-height: 0 !important;
  background: transparent !important; border: 0 !important; color: var(--ll-accent) !important;
  text-decoration: underline; font-weight: 600 !important; box-shadow: none !important;
  padding: 4px 0 !important; width: auto; align-self: flex-start; }

/* Video */
.ll-player { position: relative; }
.ll-menus { position: absolute; top: 10px; right: 10px; display: flex; gap: 8px; z-index: 3;
  opacity: 0; transition: opacity .15s; }
.ll-player:hover .ll-menus, .ll-player:focus-within .ll-menus { opacity: 1; }
.ll-menu { position: relative; }
.ll-btn { min-width: 56px; min-height: 36px; padding: 0 12px; border-radius: 10px; border: 0;
  background: rgba(0, 0, 0, 0.72); color: #fff; font-weight: 800; cursor: pointer; }
.ll-pop { position: absolute; right: 0; top: 42px; min-width: 170px; padding: 6px;
  border-radius: 12px; background: rgba(0, 0, 0, 0.88); display: flex; flex-direction: column; }
.ll-pop[hidden] { display: none; }
.ll-pop button { text-align: left; padding: 10px 12px; border: 0; border-radius: 8px;
  background: transparent; color: #fff; font-size: 1rem; cursor: pointer; }
.ll-pop button:hover { background: rgba(255, 255, 255, 0.16); }
.ll-warn { margin: 8px 0 0; padding: 10px 14px; border-radius: 10px; background: #fff3cd;
  color: #5c4400; }
.ll-warn[hidden] { display: none; }
.ll-pop button.on { background: var(--ll-accent); font-weight: 800; }
video::cue { font-size: 1.3em; background: rgba(0, 0, 0, 0.78); color: #ffffff; }

@media (max-width: 900px) {
  #shell.tabs { grid-template-columns: minmax(0, 1fr); }
  #shell > .tab-wrapper { grid-column: 1; position: static; }
  #shell > .tabitem { grid-column: 1; }
  .gradio-container { padding: 0 16px 40px !important; }
  #topbar { margin: 0 -16px 18px; padding: 12px 16px; }
  [data-testid="checkbox-group"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .nav-bar > * { min-width: 0; }
}
"""
