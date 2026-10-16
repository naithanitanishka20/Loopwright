# Phase 11 · The playground

Tag: `phase-11`

The app becomes part of the site. Served with it, on Railway or with `loopwright serve --site site`, the app is the site's playground: the site's look and header, rooms coloured by type, and a model view that shows whatever design is on screen as the site's scale model, with its signal running round each ring and every leg ready to cut.

## Exit check

| Check | Target | Result |
|---|---|---|
| Every feature in the playground | plan by id, upload (PNG, JPEG, PDF, DXF), draw, edit, cut, zone rule, installer pack, download, validator | the same app, every control kept; `tests/e2e/test_app.py` runs on its own and as the playground |
| The playground looks like the site | paper, ink, the logo's nameplate, a way back | the site's tokens and fonts, the logo plate and "Playground" on the left, Overview, Features, GitHub and the settings gear on the right |
| A model of any design | the design on screen as the site's scale model, live | `/api/solve` returns the model when asked (`"model": true`), so a solve is never repeated; the model view runs the signal and cuts legs like figure 1, and a new design replaces the old model and its listeners |
| The site leads to it | only where it exists | on a hosted copy the hero's first button is "Open the playground" and the header links to it; a static copy keeps "Run it on your machine" and shows no dead link |
| Railway | a domain works as soon as it is made | the container answers to any host name |

## How it fits together

- **One page, two ways.** `render_app(site=False)` is the app on its own, as `loopwright serve` gives it; `render_app(site=True)` adds the site's fonts, its model styles (`/figure.css`), the model script (`/model.js`), the site's links and the Plan/Model switch. Both draw the plan in the site's colours: rooms by type, cables by hub.
- **One model script.** The signal and the cuts moved from `site/main.js` into `site/model.js`, which figure 1 and the playground share. It returns a handle that stops the model, so the playground can replace it after every solve.
- **Every site page knows the app is there.** With `--site`, the server marks each top-level page, not just the front page, so the playground links show on the settings page too.
- **Model styles kept to the model.** Every generic rule in `figure.css` now sits under the model's own root, so the playground's plan drawing, which also has rooms, keeps its colours.

## Railway

The first deployment was built before the push that brought the `Dockerfile` reached `main`, so Railway's own builder guessed and stopped ("No start command detected"). Builds from this `main` use the `Dockerfile`. The container now answers to any host name: the host check exists for the app on someone's own machine, where it stops a web page reaching it through DNS rebinding, and a public service gains nothing from it.

## Still open

- **The walkable-area fault from Phase 9**: on 10 ResPlan plans rooms joined by a door are left apart and get extra hubs. Kept as a strict expected-failure test.
- The hosted app has no rate limit; its CPU time is the cost to watch.

## Run

```bash
loopwright site
python -m pytest -q
loopwright serve --site site        # the site at http://127.0.0.1:8000/, the playground at /app/
```
