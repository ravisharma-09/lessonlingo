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
</div>
"""

FORCE_LIGHT_JS = """(() => {
  const boot = () => {
  const light = () => document.body.classList.remove('dark');
  light();
  new MutationObserver(light).observe(document.body, {
    attributes: true,
    attributeFilter: ['class'],
  });
  let timer = null;
  let started = 0;
  const overlay = () => {
    let box = document.getElementById('ll-busy');
    if (!box) {
      box = document.createElement('div');
      box.id = 'll-busy';
      box.hidden = true;
      box.innerHTML = '<div class="card"><div class="spin"></div><p class="msg"></p>' +
        '<p class="sub"></p><p class="time"></p></div>';
      document.body.appendChild(box);
    }
    return box;
  };
  window.llDone = () => {
    const box = overlay();
    box.hidden = true;
    if (timer) { clearInterval(timer); timer = null; }
  };
  window.llBusy = (message, hint) => {
    const box = overlay();
    box.querySelector('.msg').textContent = message;
    box.querySelector('.sub').textContent = hint || '';
    box.hidden = false;
    started = Date.now();
    const time = box.querySelector('.time');
    time.textContent = '0 s';
    if (timer) clearInterval(timer);
    timer = setInterval(() => {
      time.textContent = Math.round((Date.now() - started) / 1000) + ' s';
    }, 500);
  };
  // Every button shows it was pressed, so a slow step never looks frozen.
  document.addEventListener('click', (event) => {
    const button = event.target.closest('button.primary, button.secondary');
    if (!button) return;
    button.classList.add('ll-pressed');
    setTimeout(() => button.classList.remove('ll-pressed'), 900);
  });
  // A failed step shows an error message: never leave the loader on top of it.
  new MutationObserver(() => {
    const box = document.getElementById('ll-busy');
    if (!box || box.hidden) return;
    if (document.querySelector('.toast-body.error, .toast-wrap .error')) window.llDone();
  }).observe(document.body, { childList: true, subtree: true });
  };
  if (document.body) boot();
  else document.addEventListener('DOMContentLoaded', boot);
})();"""

# These run before a step and hand its inputs on unchanged, so they work in any Gradio 6 version.
LOADING_LISTEN_JS = (
    "(...args) => { window.llBusy('Listening to the lecture', "
    "'Speech recognition takes about 15 seconds for every minute of audio.'); return args; }"
)
LOADING_TRANSLATE_JS = (
    "(...args) => { window.llBusy('Translating and making your files', "
    "'A dubbed voice takes a few minutes. Please keep this tab open.'); return args; }"
)
LOADING_DONE_JS = "() => { window.llDone(); window.scrollTo({ top: 0, behavior: 'smooth' }); }"

# Put in the page head, so it runs the same way in every Gradio 6 version (launch(js=) differs).
LIGHT_HEAD = (
    '<meta name="color-scheme" content="light">'
    "<style>html, body { background: #f8f4f1; color-scheme: light; }</style>"
    "<script>" + FORCE_LIGHT_JS + "</script>"
)

SCROLL_TOP_JS = "() => { window.scrollTo({ top: 0, behavior: 'smooth' }); }"

STYLE_CSS = """
@import url("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&display=swap");
/* One theme: warm paper page, dark menu panel, one orange accent. */
:root {
  --ll-accent: #c2410c; --ll-accent-hi: #f97316; --ll-accent-ink: #ffffff;
  --ll-soft: #fbebe0; --ll-soft-text: #7c2d12; --ll-surface: #ffffff; --ll-page: #f8f4f1;
  --ll-border: #ecdfd6; --ll-line: #ecdfd6; --ll-text: #1a1412; --ll-muted: #5c4f49;
  --ll-off: #9a8a82; --ll-night: #1a1210; --ll-night-text: #b8aca5;
  --ll-display: "Bricolage Grotesque", "Avenir Next", Figtree, system-ui, sans-serif;
}
/* Gradio's own accent follows ours, so no stray green is left in any component. */
:root {
  --primary-50: var(--ll-soft); --primary-100: var(--ll-soft); --primary-200: var(--ll-soft);
  --primary-300: var(--ll-accent-hi); --primary-400: var(--ll-accent-hi);
  --primary-500: var(--ll-accent); --primary-600: var(--ll-accent); --primary-700: var(--ll-accent);
  --color-accent: var(--ll-accent); --color-accent-soft: var(--ll-soft);
  --block-label-background-fill: transparent; --block-label-text-color: var(--ll-muted);
  --checkbox-background-color-selected: var(--ll-accent);
  --checkbox-border-color-selected: var(--ll-accent);
  --button-primary-background-fill: var(--ll-accent);
  --button-primary-background-fill-hover: var(--ll-accent);
}
html, body, gradio-app, main, .app, .wrap, .gradio-container {
  background: var(--ll-page) !important; }
body, .gradio-container { color: var(--ll-text); }

/* Page shell: full width, teal band on top, menu on the left, page on the right. */
.gradio-container { max-width: 1760px !important; margin: 0 auto !important;
  padding: 0 28px 40px !important; font-size: 17px; }
.html-container { padding: 0 !important; }
footer { display: none !important; }
.form { background: transparent !important; border: 0 !important; box-shadow: none !important;
  gap: 18px !important; }
span[data-testid="block-info"], .block label > span { color: var(--ll-muted) !important;
  font-weight: 700; }
.block:has(button input[type="file"]) { height: auto !important; }
fieldset.block { padding: 0 !important; border: 0 !important; background: transparent !important; }

#topbar { display: flex; align-items: center; gap: 12px; margin: 0 0 18px; padding: 18px 4px 6px; }
#topbar .logo { flex: none; transition: transform .2s; }
#topbar:hover .logo { transform: rotate(-4deg) scale(1.05); }
#topbar b span { color: var(--ll-accent); }
#topbar .mark-unused { width: 36px; height: 36px; border-radius: 10px; background: var(--ll-accent);
  color: #fff !important; display: grid; place-items: center; font-weight: 900; font-size: 1.2rem; }
#topbar b { font-family: var(--ll-display); font-size: 1.5rem; letter-spacing: -.02em; color: var(--ll-text) !important; }
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
button.upload-container, button:has(> input[type="file"]) { min-height: 160px; padding: 44px 16px 20px !important;
  border: 2px dashed var(--ll-accent) !important;
  background: var(--ll-soft) !important; border-radius: 16px !important;
  color: var(--ll-soft-text) !important; }
button:has(> input[type="file"]) * { color: var(--ll-soft-text) !important; }

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

/* Tables (Check text, lesson review): same fonts and colours as the rest */
.table-wrap, .table-wrap * { font-family: "Figtree", system-ui, sans-serif !important; }
.table-wrap { border: 1px solid var(--ll-border) !important; border-radius: 20px !important;
  background: var(--ll-surface) !important; overflow: hidden; }
.table-wrap th { background: var(--ll-soft) !important; color: var(--ll-soft-text) !important;
  font-size: 0.95rem !important; font-weight: 800 !important; letter-spacing: 0.02em; }
.table-wrap td, .table-wrap td * { font-size: 1.05rem !important; color: var(--ll-text) !important; }
.table-wrap td { padding: 10px 12px !important; }
.table-wrap tr:hover td { background: var(--ll-soft) !important; }
.table-wrap td:focus-within, .table-wrap td.focus { outline: 2px solid var(--ll-accent) !important;
  outline-offset: -2px; }
.table-wrap input, .table-wrap textarea { color: var(--ll-text) !important; }

/* One loader only: ours. Hide Gradio's own orange spinner and progress boxes. */
[data-testid="status-tracker"], .generating, .progress-bar-wrap { display: none !important; }
div.wrap.translucent { display: none !important; }

/* Pressed buttons and the hidden status line */
button.primary:active, button.secondary:active { transform: scale(0.96); }
button.ll-pressed { opacity: 0.75; pointer-events: none; position: relative; }
button.ll-pressed::after { content: ""; position: absolute; right: 18px; top: 50%;
  width: 16px; height: 16px; margin-top: -8px; border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.5); border-top-color: currentColor;
  animation: ll-spin 0.7s linear infinite; }
#ll-status { position: absolute; width: 1px; height: 1px; overflow: hidden; opacity: 0;
  pointer-events: none; }

/* Loading overlay */
#ll-busy { position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center;
  background: rgba(248, 244, 241, 0.86); backdrop-filter: blur(4px); }
#ll-busy[hidden] { display: none; }
#ll-busy .card { background: var(--ll-surface); border: 1px solid var(--ll-border);
  border-radius: 28px; padding: 36px 44px; text-align: center; max-width: 460px;
  box-shadow: 0 20px 60px rgba(14, 20, 20, 0.15); }
#ll-busy .spin { box-sizing: border-box; width: 54px; height: 54px; margin: 0 auto 20px;
  border-radius: 50%; border-style: solid !important; border-width: 5px !important;
  border-color: var(--ll-soft) !important; border-top-color: var(--ll-accent) !important;
  animation: ll-spin 0.9s linear infinite; }
#ll-busy .msg { font-family: var(--ll-display); font-size: 1.6rem; font-weight: 800;
  letter-spacing: -0.02em; margin: 0 0 8px; color: var(--ll-text); }
#ll-busy .sub { margin: 0 0 12px; color: var(--ll-muted); }
#ll-busy .time { margin: 0; color: var(--ll-off); font-variant-numeric: tabular-nums; }
@keyframes ll-spin { to { transform: rotate(360deg); } }

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
