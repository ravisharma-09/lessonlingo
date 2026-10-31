# LessonLingo site

A static page (no build step) with the specs, setup guide and a slot for the proof video.

- Preview: `python3 -m http.server 8099 --directory site`, then open http://127.0.0.1:8099
- Proof video: drop `site/media/demo.mp4` (and optionally `poster.jpg`). The page shows it by itself.
- Deploy on Vercel: import the GitHub repo and set **Root Directory** to `site`
  (Framework preset: Other, no build command, no output directory).
