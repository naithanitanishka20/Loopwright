# Phase 9 · Site remake: scale models, features and settings

Tag: `phase-9`

The product site rebuilt to show the product as a real thing. Each figure is now an isometric scale model of a solved ResPlan plan, built from the solver's own output, and the first one is live. The header gains a features menu and a settings page, and the app opens straight into a mode from a link.

## Exit check

| Check | Target | Result |
|---|---|---|
| The models are the solver's output | walls, doors, windows, rooms, nodes, hubs and every leg as solved | `tests/unit/test_figure.py`: every node, hub and leg is built, ring positions run in order, each visible leg has one joint that can be cut, a real plan is glazed with its doors open |
| Depth order is measured | wherever two parts overlap on screen, the nearer is drawn on top | rays through each overlap decide (`loopwright/iso.py`); `tests/unit/test_iso.py` has a case where sorting by centre depth alone hides a box behind a wall |
| Figure 1 lives | a signal runs round each ring and lights each socket; a cut leg is fed from both ends; pointer, keyboard and button; still under reduced motion | `tests/e2e/test_site.py` |
| Features | six buttons in a menu; a section per feature with a real screenshot and a link that opens the app in that mode | `tests/e2e/test_site.py`; the app reads the link in `tests/e2e/test_app.py` |
| Settings page | all 24 settings with their defaults, from the code | `test_the_settings_page_shows_every_setting_with_its_default`, and in the browser |
| The tests catch breakage | each behaviour | 20 deliberate breakages of the page, the figure and the generator; every one fails a test except one that cannot show (the settings page's script fill, whose fallback text equals the data by design and is checked separately) |

## On the page

- **Figure 1, plan 2916.** A model on a baseboard with feet, corner screws, a metre ruler and a label plate. Walls stand up from the wall layer with the doors open and the windows glazed (both are gaps in that layer); floors are tinted by zone; each node is a floor socket, each hub a switch box that turns or shrinks to clear the walls, and each ring's cable lies along the solver's own route with rounded bends and terminal dots. A signal leaves each hub and runs round its ring, lighting each socket as it arrives. "Cut a leg", a click on any cable or Enter on the keyboard cuts a leg: two signals then leave the hub, one each way, and still reach every socket. The readout says where the signal is or how many sockets are fed. Every few laps an idle tour cuts the longest leg.
- **Figures 2 and 3**, the door rule on plan 16448 and before and after on plan 11282, as models with each ring's cable in its zone's colour. Past three zones the colours go by role: the living room's zone, one-room zones, the rest.
- **Figures 4 and 5**, the charts, and **figures 6 to 11**, the app's six features: edit a plan and re-solve, cut the cable, the installer pack with loop resistance, drawing a plan, DXF import, and photo or PDF upload.
- **The settings page**, every rule reading with its default and its question in `docs/assumptions.md`, behind the settings icon at the top left.

## Design

- The figures follow a technical-illustration method: a real object whose working is the concept, built from many small parts; four tones by facing and a lighter top; 0.6 px lines, each ending on another line, a dot or an outline; one lit accent, the signal; framed cards with the figure number, a title, a hint and a live readout.
- Phones see the model 18% larger inside its card, and the card's control and readout keep apart.
- Drawings that only stand in for visitors without scripts load lazily, so they are not downloaded twice.

## Code review and audit

A review of this phase's changes and an audit of the whole repository. Fixed in this phase:

- Two zones of plan 16448 shared a colour; legs too short to see could be picked from the keyboard; fallback drawings downloaded twice; a test line checked nothing; "See the features" skipped the note that the app must be running.
- **The exact search walked every subset of the rooms with no limit**, so a large sketch in the app (say 24 rooms) froze the server. Plans with more than 14 eligible rooms are now refused with the reason; ResPlan has at most 10.
- **PDF pages bypassed the image size limit.** An A0 drawing at 300 dpi is about 139 million pixels. Pages and images now share one limit, checked before anything is rendered.

Still open, for the next phase:

- **On 10 ResPlan plans the walkable area leaves rooms apart although the door graph joins them,** so each piece gets its own hub: plan 1180 gets 4 hubs against a lower bound of 1, plans 12735 and 8111 get 3 against 1; 14 hubs in all above the greedy baseline, which ignores walkability. A hand-drawn three-room image shows the same and is kept as a strict expected-failure test (`tests/unit/test_import_image.py`). The fix is in the geometry (the walkable area must pass every door the door graph knows) and needs the full batch run again.

## Run

```bash
loopwright site
python -m pytest tests/unit/test_iso.py tests/unit/test_figure.py tests/unit/test_site.py tests/unit/test_site_page.py tests/e2e/test_site.py tests/e2e/test_app.py -q
```

Then open `site/index.html`.
