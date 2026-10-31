"""Look and feel of the web UI: slim pixel header, step bar and one set of spacing rules."""

from __future__ import annotations

HERO_HTML = """
<div id="topbar">
  <span class="mark" aria-hidden="true">L</span>
  <b>LessonLingo</b>
  <span class="tag">Translate lectures and lessons. Works offline.</span>
</div>
"""

FORCE_LIGHT_JS = """() => {
  const url = new URL(window.location);
  if (url.searchParams.get('__theme') !== 'light') {
    url.searchParams.set('__theme', 'light');
    window.location.href = url.href;
  }
}"""

SCROLL_TOP_JS = "() => { window.scrollTo({ top: 0, behavior: 'smooth' }); }"

STYLE_CSS = """
/* One theme: white surfaces, one teal accent. */
:root, body {
  --ll-accent: #0f766e; --ll-accent-ink: #ffffff; --ll-soft: #e8f5f3; --ll-soft-text: #0b4b46;
  --ll-surface: #ffffff; --ll-page: #f6f8f8; --ll-border: #dbe5e3; --ll-line: #dbe5e3;
  --ll-text: #14201f; --ll-muted: #52615f; --ll-off: #8a9896;
}
body, .gradio-container { background: var(--ll-page) !important; color: var(--ll-text); }

/* Page shell: full width, teal band on top, menu on the left, page on the right. */
.gradio-container { max-width: 1760px !important; margin: 0 auto !important;
  padding: 0 28px 40px !important; font-size: 17px; }
.html-container { padding: 0 !important; }
footer { display: none !important; }
.form { background: transparent !important; border: 0 !important; box-shadow: none !important; }
fieldset.block { padding: 0 !important; border: 0 !important; background: transparent !important; }

#topbar { display: flex; align-items: center; gap: 12px; background: var(--ll-surface);
  border-bottom: 1px solid var(--ll-border); margin: 0 -28px 24px; padding: 14px 28px; }
#topbar .mark { width: 36px; height: 36px; border-radius: 10px; background: var(--ll-accent);
  color: #fff !important; display: grid; place-items: center; font-weight: 900; font-size: 1.2rem; }
#topbar b { font-size: 1.3rem; color: var(--ll-text) !important; }
#topbar .tag { color: var(--ll-muted) !important; font-size: .95rem; }

#shell.tabs { display: grid !important; grid-template-columns: 290px minmax(0, 1fr); gap: 32px;
  align-items: start; }
#shell > .tab-wrapper { grid-column: 1; position: sticky; top: 16px; height: auto !important;
  background: var(--ll-surface); border: 1px solid var(--ll-border); border-radius: 18px;
  padding: 12px; }
#shell > .tab-wrapper .tab-container { flex-direction: column !important; height: auto !important;
  gap: 4px; align-items: stretch; }
#shell > .tab-wrapper .tab-container::after { display: none !important; }
#shell > .tab-wrapper .overflow-menu { display: none !important; }
#shell > .tab-wrapper button[role="tab"] { text-align: left; justify-content: flex-start;
  padding: 14px 16px !important; border-radius: 12px !important; border: 0 !important;
  font-size: 1.02rem; font-weight: 600; color: var(--ll-muted) !important;
  background: transparent !important; height: auto !important; }
#shell > .tab-wrapper button[role="tab"]:hover { background: var(--ll-soft) !important; }
#shell > .tab-wrapper button[role="tab"].selected::after { display: none !important; }
#shell > .tab-wrapper button[role="tab"].selected { background: var(--ll-soft) !important;
  color: var(--ll-accent) !important; font-weight: 800; }
#shell > .tab-wrapper button[role="tab"]:disabled { opacity: .45; cursor: not-allowed; }
#shell > .tab-wrapper button[role="tab"]:nth-child(6) { margin-top: 14px; position: relative; }
#shell > .tabitem { grid-column: 2; padding: 0 !important; border: 0 !important; }

.page { gap: 20px !important; padding-bottom: 12px; }
.page-head h2 { font-size: 2rem; font-weight: 800; margin: 0 0 6px; color: var(--ll-text); }
.page-head p { margin: 0; color: var(--ll-muted); font-size: 1rem; }
.hint, .hint p { color: var(--ll-muted) !important; font-size: 0.98rem; }
.split { gap: 28px !important; align-items: flex-start !important; }
.split > * { min-width: 0; }
.side-card { background: var(--ll-surface); border: 1px solid var(--ll-border);
  border-radius: 18px; padding: 22px !important; gap: 18px !important; }
.side-card h3 { margin-top: 0; }
.nav-bar { position: sticky; bottom: 0; z-index: 5; background: var(--ll-page);
  border-top: 1px solid var(--ll-border); padding: 14px 0 !important; gap: 12px !important;
  justify-content: flex-end; }
.nav-bar > * { flex: 0 1 auto !important; min-width: 200px; }

/* Drop area */
button.upload-container { border: 2px dashed var(--ll-accent) !important;
  background: var(--ll-soft) !important; border-radius: 16px !important;
  color: var(--ll-soft-text) !important; }
button.upload-container * { color: var(--ll-soft-text) !important; }

/* Choice tiles: big, with a visible selected state. */
[data-testid="checkbox-group"] { display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
[data-testid="checkbox-group"] label, label[data-testid$="-radio-label"] {
  display: flex !important; align-items: center; gap: 10px; min-height: 54px;
  padding: 12px 16px !important; font-size: 1.02rem; cursor: pointer;
  border-radius: 14px !important; border: 2px solid var(--ll-border) !important;
  background: var(--ll-surface) !important; box-shadow: none !important;
  color: var(--ll-text) !important; }
[data-testid="checkbox-group"] label:hover, label[data-testid$="-radio-label"]:hover {
  border-color: var(--ll-accent) !important; }
[data-testid="checkbox-group"] label.selected, label[data-testid$="-radio-label"].selected {
  border-color: var(--ll-accent) !important; background: var(--ll-soft) !important;
  color: var(--ll-soft-text) !important; font-weight: 700; }
[data-testid="checkbox-group"] label.selected::after,
label[data-testid$="-radio-label"].selected::after {
  content: "\\2713"; margin-left: auto; color: var(--ll-accent); font-weight: 800; }
[data-testid="checkbox-group"] input, label[data-testid$="-radio-label"] input {
  position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
[data-testid="checkbox-group"] label span,
label[data-testid$="-radio-label"] span { margin: 0 !important; }
div:has(> label[data-testid$="-radio-label"]) { display: grid !important; gap: 10px; }
.lang-chips div:has(> label[data-testid$="-radio-label"]) {
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }

/* Buttons */
button.primary, .primary { min-height: 54px; font-size: 1.08rem !important; font-weight: 800 !important;
  border-radius: 14px !important; background: var(--ll-accent) !important;
  color: var(--ll-accent-ink) !important; border: 0 !important; }
button.secondary { min-height: 54px; font-size: 1.05rem !important; font-weight: 700 !important;
  border-radius: 14px !important; background: var(--ll-surface) !important;
  color: var(--ll-accent) !important; border: 2px solid var(--ll-accent) !important; }
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
