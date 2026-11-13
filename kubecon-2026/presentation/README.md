# Presentation

Open [`deck.html`](deck.html) directly in a browser. It contains the slides, fonts, graphics, and presentation framework in one file. Use the arrow keys to navigate.

The editable slide content is in `content/slides.md`. To rebuild both the standalone deck and the served version after editing:

```sh
python3 scripts/build.py
python3 -m http.server 8000
```

Then open <http://localhost:8000/>. The served `index.html` loads its Markdown and SVGs over HTTP, so it should not be opened directly as a file. The published build omits my rehearsal notes. I clarified a few headlines and labels after the talk to make it clear that the observations apply to these runs, not to the projects as a whole. I keep the original presentation in my local archive.
