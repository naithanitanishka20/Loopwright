# Phase 12 · The playground in the site's own header and footer

Tag: `phase-12`

The playground now is the site rather than looking like it: the same stylesheet, the same header with its Features menu and its links, the same title block at the foot, a page title like the settings page's, and it opens on a solved plan shown as a model.

## Exit check

| Check | Target | Result |
|---|---|---|
| One look | the playground styled by the site itself | served with the site, the page links `styles.css` and `main.js`; the app's own styles keep to its layout, scoped to `#app` and `#plan` |
| One header and footer | never a copy that drifts | the server takes the header and the footer from the site's `index.html` when it starts, makes their links absolute for `/app/`, and marks the Playground link as the current page |
| Opens alive | not an empty form | with the plans present and no mode in the link, the playground solves plan 16448 and shows it as a model |
| On its own | `loopwright serve` without the site | unchanged: the app's own header and the site's look carried in the page |

## Changes

- `render_app(site_dir)` reads the site's header and footer; the page is rendered once when the server starts.
- `main.js` drops its scripts-on mark only on pages whose figures need `data.js`, so the playground's menu keeps working without it.
- The playground widens the site's `--max` to 1480 px, so the app has room and the intro, the panels and the title block line up.

## Railway

Railway builds a push only when its GitHub app can see the repository. The first deployment ran before the push that brought the `Dockerfile`, and no later push reached Railway, so its "Redeploy" kept rebuilding that first commit. The README now says how to connect the app, or how to deploy from a checkout with the Railway CLI.

## Still open

- **The walkable-area fault from Phase 9** (10 ResPlan plans get extra hubs), kept as a strict expected-failure test.
- The hosted app has no rate limit.

## Run

```bash
loopwright site
python -m pytest -q
loopwright serve --site site        # the site at http://127.0.0.1:8000/, the playground at /app/
```
