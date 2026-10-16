# Phase 10 · Pull requests merged, the site redrawn, a hosted copy

Tag: `phase-10`

The three open pull requests are merged. The product site is redrawn as an installer's working drawing, its figures rebuilt as architectural models with raised walls and rooms coloured and named by type, and the site and the app now run together as one hosted service on Railway.

## Exit check

| Check | Target | Result |
|---|---|---|
| Pull requests #3, #4 and #5 merged | each a merge commit, so GitHub marks it merged on push; nothing they test is lost | #3 changes no file (its branch had already taken `main`'s version of everything); #4 merged with one conflict, both sides' tests kept; #5 merged, then one room limit instead of two (below) |
| The site no longer looks generated | its own visual language, the logo where it stands out | drafting paper with a graph grid, ink linework, the logo's blue for anything you can press, pencil notes where a person would mark up a plan, a title block at the foot; the logo in its own white-on-black form as the header's nameplate |
| Settings gear | at the corner of the pane with the section links | the last cell of the right-hand pane, `tests/e2e/test_site.py` at 1440 and 390 px |
| How it works | each answer appears while its question is hovered | six questions; an answer opens on hover, on keyboard focus, or on a tap where there is no pointer; without scripts every answer stays open |
| The models | raised walls, rooms coloured by type, rooms labelled, built properly | walls cut at 1.1 m seen from 50°, windows glazed above a sill with a jamb at each end, floors tinted by type and laid with planks or tiles, every room named with its area on its floor, one sun's shadows, a plinth with a scale bar in true metres |
| Room colours tell apart | for everyone | living orange, bedroom sky blue, kitchen green, storage orchid, bathroom grey; worst pair ΔE 17.2 for normal vision and 9.3 under colour-vision deficiency (palette checker, all pairs); every room is also named |
| Hosted copy | the site at `/`, the app at `/app/`, from the repository | `loopwright serve --site site`, a `Dockerfile` and `railway.json`; rehearsed locally with the container's own start command |

## Pull requests

- **#3, Phases 3 & 4.** Its last commit merged `main` and kept `main`'s version of every file, so the merge records the branch's history and changes nothing.
- **#4, Phase 5 and 6 hardening.** Finite-number checks across the API, CLI, sketch builder, image importer and batch runner, malformed doors refused, a cap on batch workers, and a CI job for the browser tests. Its tests and the Phase 9 tests both landed at the end of `tests/unit/test_import_image.py`; both are kept. The site's browser tests now carry the `e2e` mark, so that CI job runs them too.
- **#5, a bound on the exact search.** Phase 9 had capped `solve()` at 14 eligible rooms; #5 capped the zone search itself at 12. The zone search's check refuses even an 80-room sketch in 0.12 s, so it is the one limit now, with Phase 9's message: the room count and what to do.

## On the page

- **Header.** Two panes. The left holds the logo plate and the Features menu with the six features; the right holds How it works, Results, Run it, GitHub and, in its corner, the settings gear. On phones the right pane keeps the gear.
- **Hero.** The claim as the headline, "The fewest hubs, then the least cable.", with two pencil notes, then the live model.
- **Figures.** Each sits on a framed drawing panel with its number, title, hint and live readout. Figure 1 still runs a signal round each ring, now in the logo's cyan on the cable, and a cut shows its two ends in red.
- **Charts** in a paper theme: the logo's blue and a burnt orange, both clear of 3:1 against the panel.
- **Fonts**, all under the SIL Open Font License and served from the site: Instrument Sans for headings and text, IBM Plex Mono for labels and code, Architects Daughter for the pencil notes, Outfit for the wordmark.

## Hosting

`loopwright serve --site site` serves the built site at `/` and the app at `/app/`, and marks the page so the site's "Open in the app" buttons open that app and hide the note about running it locally. `--allow-host` names the public domain the server answers to.

The `Dockerfile` installs the package, downloads ResPlan against its pinned SHA-256, and keeps only the test split and the three plans the site opens (`scripts/hosted_plans.py`): 1,635 plans and about 150 MB of memory once loaded, against 1.4 GB for all 17,000. Railway supplies the port and the public domain; `railway.json` names the Dockerfile and a health check on `/`.

## Code review

A review of this phase's changes. Fixed before the merge:

- On a touch screen a second tap left an answer open, because the button kept the focus. There, answers now follow the tap alone; hover and focus open them only where there is a pointer.
- Every stop of the live figure carried its room's name, which nothing read; dropped.
- The label test passed even with obstacles ignored; it now puts the socket where the label would otherwise go.
- Opened from disk, the font preload failed (a cross-origin request on `file://`); removed, and the fonts still load.
- On the hosted copy the notes about running the app locally stayed visible, because their own display rule beat `hidden`; `[hidden]` now wins.
- Under reduced motion the logo's loop still animated; it is now drawn at once.
- The header hid its section links below 1080 px, though they fit down to 760 px.

Sixteen deliberate breakages of the models, the page, the server and the hosted subset each fail a test.

Not changed, worth knowing: the hosted app is public with no rate limit, so anyone can make it solve a plan or parse an upload. Its CPU time is the cost to watch (about 0.4 s a solve; uploads stay capped at 20 MB). The image build loads all 17,000 plans once, about 1.4 GB, to cut the subset.

## Still open

- **The walkable-area fault from Phase 9**: on 10 ResPlan plans rooms joined by a door are left apart, so they get extra hubs. Kept as a strict expected-failure test; the fix is in the geometry and needs the full batch run again.

## Run

```bash
loopwright site
python -m pytest -q
loopwright serve --site site        # the site at http://127.0.0.1:8000/, the app at /app/
```
