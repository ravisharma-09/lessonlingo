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
/* Colours are variables so light and dark both look right. */
:root {
  --ll-surface: #ffffff; --ll-border: #d3e4d9; --ll-text: #12261b; --ll-muted: #3f5648;
  --ll-soft: #e8f7ed; --ll-soft-text: #0f3d22; --ll-accent: #16803c; --ll-accent-ink: #ffffff;
  --ll-drop: #f1faf4; --ll-drop-text: #0f5a2b; --ll-off: #6a7a70; --ll-line: #d3e4d9;
}
.dark {
  --ll-surface: #16251c; --ll-border: #2f4a3a; --ll-text: #eaf5ee; --ll-muted: #a8c2b2;
  --ll-soft: #1d3a29; --ll-soft-text: #d6f5e0; --ll-accent: #3ecf6e; --ll-accent-ink: #0b1d12;
  --ll-drop: #14231a; --ll-drop-text: #bfe8cd; --ll-off: #8aa595; --ll-line: #2f4a3a;
}

/* One spacing system: wide page, 22px between blocks, 10px between tiles, 56px controls. */
.gradio-container { max-width: 1120px !important; margin: 0 auto !important;
  padding-left: 28px !important; padding-right: 28px !important; font-size: 17px; }
.tabitem, .tab-wrapper { padding-left: 0 !important; padding-right: 0 !important; }
.html-container { padding: 0 !important; }
.form { background: transparent !important; border: 0 !important; box-shadow: none !important;
  gap: 0 !important; }
fieldset.block { padding: 0 !important; border: 0 !important; background: transparent !important; }
footer { display: none !important; }
.step-body { display: flex !important; flex-direction: column; gap: 24px !important;
  padding-top: 18px; padding-bottom: 28px; }
.split { gap: 36px !important; align-items: flex-start !important; }
.split > * { min-width: 0; }

/* Header */
#topbar { display: flex; align-items: center; gap: 14px; padding: 6px 0 12px; }
#topbar .tile { background: #2d4540; border-radius: 14px; padding: 8px 12px; display: flex;
  gap: 8px; align-items: flex-end; }
#topbar .tile svg { image-rendering: pixelated; }
#topbar .brand { display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }
#topbar .brand b { font-size: 1.45rem; letter-spacing: -.01em; color: var(--ll-text); }
#topbar .brand span { font-size: 0.92rem; color: var(--ll-muted); }

/* Step bar */
.stepper { list-style: none; display: flex; align-items: center; gap: 0; margin: 22px 0 0;
  padding: 0; max-width: 640px; }
.stepper li { display: flex; align-items: center; gap: 10px; flex: 1; color: var(--ll-off);
  font-weight: 600; height: 34px; }
.stepper li:last-child { flex: 0 0 auto; }
.stepper li:not(:last-child)::after { content: ""; flex: 1; height: 2px; margin: 0 12px;
  background: var(--ll-line); }
.stepper .dot { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center;
  border: 2px solid var(--ll-line); font-weight: 800; background: var(--ll-surface);
  color: var(--ll-off); }
.stepper li.current { color: var(--ll-text); }
.stepper li.current .dot { background: var(--ll-accent); border-color: var(--ll-accent);
  color: var(--ll-accent-ink); }
.stepper li.done { color: var(--ll-accent); }
.stepper li.done .dot { border-color: var(--ll-accent); color: var(--ll-accent); }
.stepper li.done:not(:last-child)::after { background: var(--ll-accent); }

/* Headings and help text */
.step h3 { margin: 0 0 4px; font-size: 1.35rem; font-weight: 800; line-height: 1.2;
  color: var(--ll-text); }
.step p { margin: 0; color: var(--ll-muted); }
.hint, .hint p { color: var(--ll-muted) !important; font-size: 0.95rem; }

/* Drop area */
button.upload-container { border: 2px dashed var(--ll-accent) !important;
  background: var(--ll-drop) !important; border-radius: 16px !important;
  color: var(--ll-drop-text) !important; min-height: 150px; }
button.upload-container * { color: var(--ll-drop-text) !important; }
button.upload-container:hover { background: var(--ll-soft) !important; }

/* Choice tiles: big, with a visible selected state. */
[data-testid="checkbox-group"] { display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
[data-testid="checkbox-group"] label, label[data-testid$="-radio-label"] {
  display: flex !important; align-items: center; gap: 10px; min-height: 56px;
  padding: 12px 16px !important; font-size: 1.05rem; cursor: pointer;
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
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }

/* Buttons */
button.primary, .primary { min-height: 56px; font-size: 1.1rem !important; font-weight: 800 !important;
  border-radius: 14px !important; }
button.secondary { min-height: 56px; font-size: 1.05rem !important; font-weight: 700 !important;
  border-radius: 14px !important; background: var(--ll-surface) !important;
  color: var(--ll-accent) !important; border: 2px solid var(--ll-accent) !important; }
.link-button, .link-button button, button.link-button { min-height: 0 !important;
  background: transparent !important; border: 0 !important; color: var(--ll-accent) !important;
  text-decoration: underline; font-weight: 600 !important; box-shadow: none !important;
  padding: 4px 0 !important; width: auto; align-self: flex-start; }
.sticky-cta { position: sticky; bottom: 14px; z-index: 5; }
.row-buttons { display: flex !important; gap: 12px !important; }
.row-buttons > * { flex: 1; }

/* Video */
video::cue { font-size: 1.3em; background: rgba(0, 0, 0, 0.78); color: #ffffff; }

@media (max-width: 700px) {
  .gradio-container { padding-left: 16px !important; padding-right: 16px !important; }
  [data-testid="checkbox-group"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  #topbar .brand span { font-size: 0.82rem; }
  .stepper .name { font-size: 0.95rem; }
}
"""
