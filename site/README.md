# LessonLingo site

A static page (no build step) with the specs, setup guide and a slot for the proof video.

- Preview: `python3 -m http.server 8099 --directory site`, then open http://127.0.0.1:8099
- Proof video: the page embeds the demo from Google Drive (the file must stay shared as "Anyone with the link"). Dropping `site/media/demo.mp4` (under about 50 MB) next to the page replaces the embed.
- Deploy on Vercel: import the GitHub repo and set **Root Directory** to `site`
  (Framework preset: Other, no build command, no output directory).
