"""Look and feel of the web UI: slim pixel header, step bar and one set of spacing rules."""

from __future__ import annotations

HERO_HTML = """
<div id="topbar">
  <div class="tile" aria-hidden="true">
    <svg viewBox="0 0 10 10" shape-rendering="crispEdges" width="34" height="34">
      <rect x="3" y="0" width="4" height="1" fill="#f4f1ea"/><rect x="2" y="1" width="6" height="1" fill="#f4f1ea"/>
      <rect x="1" y="2" width="8" height="1" fill="#f4f1ea"/><rect x="0" y="3" width="10" height="6" fill="#f4f1ea"/>
      <rect x="0" y="9" width="2" height="1" fill="#f4f1ea"/><rect x="4" y="9" width="2" height="1" fill="#f4f1ea"/>
      <rect x="8" y="9" width="2" height="1" fill="#f4f1ea"/>
      <rect x="2" y="3" width="2" height="2" fill="#1b1613"/><rect x="6" y="3" width="2" height="2" fill="#1b1613"/>
      <rect x="1" y="6" width="2" height="1" fill="#ea7b78"/><rect x="7" y="6" width="2" height="1" fill="#ea7b78"/>
      <rect x="4" y="6" width="2" height="1" fill="#1b1613"/>
    </svg>
    <svg viewBox="0 0 12 11" shape-rendering="crispEdges" width="38" height="35">
      <rect x="4" y="0" width="2" height="1" fill="#7a3b12"/><rect x="3" y="1" width="6" height="1" fill="#e2461f"/>
      <rect x="1" y="2" width="1" height="1" fill="#e2461f"/><rect x="2" y="2" width="8" height="1" fill="#f5b524"/>
      <rect x="10" y="2" width="1" height="1" fill="#e2461f"/>
      <rect x="0" y="3" width="1" height="7" fill="#e2461f"/><rect x="11" y="3" width="1" height="7" fill="#e2461f"/>
      <rect x="1" y="3" width="10" height="6" fill="#f5b524"/>
      <rect x="3" y="4" width="2" height="1" fill="#1f1a17"/><rect x="4" y="5" width="1" height="1" fill="#1f1a17"/>
      <rect x="7" y="4" width="2" height="1" fill="#1f1a17"/><rect x="7" y="5" width="1" height="1" fill="#1f1a17"/>
      <rect x="2" y="7" width="8" height="1" fill="#1f1a17"/>
      <rect x="3" y="8" width="1" height="1" fill="#1f1a17"/><rect x="5" y="8" width="2" height="1" fill="#1f1a17"/>
      <rect x="8" y="8" width="1" height="1" fill="#1f1a17"/>
      <rect x="1" y="9" width="10" height="1" fill="#f5b524"/><rect x="2" y="10" width="8" height="1" fill="#e2461f"/>
    </svg>
  </div>
  <div class="brand">
    <b>LessonLingo</b>
    <span>Free lectures in your language. Set up once, then no internet needed.</span>
  </div>
</div>
<div id="strip"></div>
"""

LECTURE_STEPS = ("Add", "Check", "Watch")
LESSON_STEPS = ("Add", "Review")


def stepper_html(current: int, labels: tuple[str, ...] = LECTURE_STEPS) -> str:
    """The step bar: finished steps get a tick, the current one is filled, the rest are plain."""

    items = []
    for number, label in enumerate(labels, start=1):
        state = "done" if number < current else "current" if number == current else "todo"
        mark = "✓" if state == "done" else str(number)
        items.append(
            f'<li class="{state}"><span class="dot">{mark}</span><span class="name">{label}</span></li>'
        )
    return f'<ol class="stepper" aria-label="Progress">{"".join(items)}</ol>'


SCROLL_TOP_JS = "() => { window.scrollTo({ top: 0, behavior: 'smooth' }); }"

STYLE_CSS = """
/* One spacing system: 720px page, 22px between blocks, 10px between tiles, 56px controls. */
.gradio-container { max-width: 720px !important; margin: 0 auto !important;
  padding-left: 18px !important; padding-right: 18px !important; font-size: 17px; }
.tabitem, .tab-wrapper { padding-left: 0 !important; padding-right: 0 !important; }
.html-container { padding: 0 !important; }
.form { background: transparent !important; border: 0 !important; box-shadow: none !important;
  gap: 0 !important; }
fieldset.block { padding: 0 !important; border: 0 !important; background: transparent !important; }
footer { display: none !important; }
.step-body { display: flex !important; flex-direction: column; gap: 22px !important;
  padding-top: 18px; padding-bottom: 28px; }

/* Header */
#topbar { display: flex; align-items: center; gap: 14px; padding: 4px 0 10px; }
#topbar .tile { background: #2d4540; border-radius: 14px; padding: 8px 12px; display: flex;
  gap: 8px; align-items: flex-end; }
#topbar .tile svg { image-rendering: pixelated; }
#topbar .brand { display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }
#topbar .brand b { font-size: 1.45rem; letter-spacing: -.01em; color: var(--body-text-color); }
#topbar .brand span { font-size: 0.92rem; color: #3f5648; }
#strip { height: 6px; border-radius: 6px; background: repeating-linear-gradient(90deg,
  #8fb4e3 0 28px, #f5b524 28px 56px, #ea7b78 56px 84px, #e2461f 84px 112px); }

/* Step bar */
.stepper { list-style: none; display: flex; align-items: center; gap: 0; margin: 22px 0 0;
  padding: 0; }
.stepper li { display: flex; align-items: center; gap: 10px; flex: 1; color: #6a7a70; height: 34px;
  font-weight: 600; }
.stepper li:last-child { flex: 0 0 auto; }
.stepper li:not(:last-child)::after { content: ""; flex: 1; height: 2px; margin: 0 12px;
  background: #d3e4d9; }
.stepper .dot { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center;
  border: 2px solid #d3e4d9; font-weight: 800; background: #ffffff; color: #6a7a70; }
.stepper li.current { color: #0f3d22; }
.stepper li.current .dot { background: #16803c; border-color: #16803c; color: #ffffff; }
.stepper li.done { color: #16803c; }
.stepper li.done .dot { border-color: #16803c; color: #16803c; }
.stepper li.done:not(:last-child)::after { background: #16803c; }

/* Headings and help text */
.step h3 { margin: 0 0 4px; font-size: 1.35rem; font-weight: 800; line-height: 1.2; }
.step p { margin: 0; color: #3f5648; }
.hint, .hint p { color: #4a6153 !important; font-size: 0.95rem; }

/* Drop area */
button.upload-container { border: 2px dashed #16803c !important; background: #f1faf4 !important;
  border-radius: 16px !important; color: #0f5a2b !important; min-height: 150px; }
button.upload-container:hover { background: #e8f7ed !important; }

/* Choice tiles: big, with a visible selected state. */
[data-testid="checkbox-group"] { display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
[data-testid="checkbox-group"] label, label[data-testid$="-radio-label"] {
  display: flex !important; align-items: center; gap: 10px; min-height: 56px;
  padding: 12px 16px !important; font-size: 1.05rem; cursor: pointer;
  border-radius: 14px !important; border: 2px solid #d3e4d9 !important;
  background: #ffffff !important; box-shadow: none !important; color: #12261b !important; }
[data-testid="checkbox-group"] label:hover, label[data-testid$="-radio-label"]:hover {
  border-color: #16803c !important; }
[data-testid="checkbox-group"] label.selected, label[data-testid$="-radio-label"].selected {
  border-color: #16803c !important; background: #e8f7ed !important; color: #0f3d22 !important;
  font-weight: 700; }
[data-testid="checkbox-group"] label.selected::after,
label[data-testid$="-radio-label"].selected::after {
  content: "\\2713"; margin-left: auto; color: #16803c; font-weight: 800; }
[data-testid="checkbox-group"] input, label[data-testid$="-radio-label"] input {
  position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
[data-testid="checkbox-group"] label span,
label[data-testid$="-radio-label"] span { margin: 0 !important; }
div:has(> label[data-testid$="-radio-label"]) { display: grid !important; gap: 10px; }
.lang-chips div:has(> label[data-testid$="-radio-label"]) {
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }

/* Buttons */
button.primary, .primary { min-height: 56px; font-size: 1.1rem !important; font-weight: 800 !important;
  border-radius: 14px !important; }
button.secondary { min-height: 56px; font-size: 1.05rem !important; font-weight: 700 !important;
  border-radius: 14px !important; background: #ffffff !important; color: #16803c !important;
  border: 2px solid #16803c !important; }
.link-button, .link-button button, button.link-button { min-height: 0 !important; background: transparent !important;
  border: 0 !important; color: #16803c !important; text-decoration: underline;
  font-weight: 600 !important; box-shadow: none !important; padding: 4px 0 !important;
  width: auto; align-self: flex-start; }
.sticky-cta { position: sticky; bottom: 14px; z-index: 5; }
.row-buttons { display: flex !important; gap: 12px !important; }
.row-buttons > * { flex: 1; }

/* Video and tables */
video::cue { font-size: 1.3em; background: rgba(0, 0, 0, 0.78); color: #ffffff; }

@media (max-width: 560px) {
  .gradio-container { padding-left: 16px !important; padding-right: 16px !important; }
  [data-testid="checkbox-group"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  #topbar .brand span { font-size: 0.82rem; }
  .stepper .name { font-size: 0.95rem; }
}
"""
