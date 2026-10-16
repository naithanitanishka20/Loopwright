# Phase 8 · Product site

Tag: `phase-8`

A static site in `site/` that explains what Loopwright does and shows it working. It sells nothing it cannot show: every drawing on it is solver output, and every figure comes from the batch records in `bench/`.

## Exit check

| Check | Target | Result |
|---|---|---|
| Drawings and figures come from the solver and `bench/` | no number typed in by hand | `loopwright site` writes `site/data.js`; `tests/unit/test_site_page.py` fails if the page's own figures drift from it |
| Opens anywhere | from disk or GitHub Pages; no CDN, web font or request to another site | `test_the_site_works_opened_straight_from_disk`, `test_the_page_loads_nothing_from_another_site` |
| Reduced motion and no scripts | the finished drawing at once; every drawing and number without scripts | `test_reduced_motion_shows_the_finished_drawing_at_once`, `test_without_scripts_every_drawing_and_number_still_shows` |
| Fits a phone | no sideways scroll at 390 px; markers stay readable | `test_the_site_fits_a_phone_and_keeps_markers_readable` |
| The browser tests catch real breakage | each interactive behaviour | 9 of 9 deliberate breakages caught (switch, wipe, hero, node lighting, reduced motion, copy, marker size, wipe layering, wordmark width) |

## On the page

- **Hero.** The wordmark's loop draws itself, then plan 2916 fades in, its hubs appear and each ring draws leg by leg in visiting order; a node lights when its cable arrives. A greedy grouping needs 3 hubs there; the solver finds 2, the lower bound. "Draw it again" replays it.
- **The rules** and **how it works**, in six steps from reading the plan to the independent check.
- **The door rule.** Plan 16448 under the own-doors rule needs 4 hubs; letting cable pass through another zone's room needs 2. A switch crossfades the two drawings and their figures.
- **Before and after.** Plan 11282 with nodes at room centres and shared lanes (J 47.1) against nodes by the doors and separate lanes (J 19.4), compared with a wipe that follows the pointer or the arrow keys.
- **Results** on all 17,000 plans, with the two charts in a dark theme.
- **The app** (a screenshot of plan 2916 solved, every rule passing) and **commands** to install and run it, for Windows or macOS and Linux, with copy buttons.

## Design

- Brand from the logo: true black, white type in Outfit (variable, SIL Open Font License, served from `site/assets/fonts/`), and the loop's cyan, azure and blue gradient. Cable colours are used only for cable.
- Walls are a grey darker than any cable colour (`test_walls_stay_quieter_than_every_cable_colour`), so the rings lead.
- Markers are drawn about their own centre, and the page scales them with the drawing, so hub labels and nodes stay readable on a phone. Hub labels move off nodes and cable.
- One choreographed animation, in the hero. Everything else moves only when the visitor acts. With reduced motion the page shows the end state; without scripts it shows still drawings.

## Other changes

- `charts.py` takes a theme: light for slides and docs (unchanged), dark for the site. Chart subtitles read as plain sentences.
- README: a product site section, and the `results` and `charts` examples now list all four splits, as the committed `bench/results.md` and `docs/figures/` use.
- Version 0.8.0.

## Run

```bash
loopwright site                                    # site/data.js and site/assets/ from bench/ and four ResPlan plans
python -m pytest tests/unit/test_site.py tests/unit/test_site_page.py tests/e2e/test_site.py -q
```

Then open `site/index.html`.

## Publishing

GitHub Pages can serve the folder: in the repository settings, Pages, choose GitHub Actions and deploy `site/`, or publish a branch with the folder at its root. Not set up yet.
