# Demo script

Five minutes for a jury of engineers. The app carries the argument; the slides frame it. Every number below comes from `bench/results.md`, except the solve time, which comes from `bench/latency-test.md` (one process). Re-generate both before rehearsing and change the numbers here only from those files.

## Before going on stage

1. Laptop on mains power, Wi-Fi off, notifications off, browser zoom 100%.
2. `loopwright serve` in a terminal; open `http://127.0.0.1:8000/` in a fresh browser window.
3. Warm it up: solve plan 16448 once (the first solve loads ResPlan, about 10 s), then reload the page.
4. Have ready: `out/16448.html` and `out/16448.installer.html` (made with `loopwright solve --id 16448 --out out/`) as a fallback if the server fails; `docs/figures/*.svg` for the proof beat; the backup video.

## The five minutes

| Time | Beat | On screen | Say |
|---|---|---|---|
| 0:00 – 0:30 | The ranking, and the catch | App, plan 16448, zone rule *strict*: 4 hubs. Switch to *through rooms*: 2 hubs. | "You rank by fewest hubs. On this plan the area says two. Your door rule, read strictly, says four. Getting that number right, provably, is most of this problem." |
| 0:30 – 1:15 | Any flat, live | Draw tab: drag a living room, a bedroom and a kitchen; tick the doors; solve. | "No dataset needed. Draw a flat and it designs the loop in under a second." |
| 1:15 – 2:00 | A judge picks the plan | Plan by id: ask a judge for any test-split number. Or Upload a plan image or DXF. | Point at the validator panel: every rule green, checked by a validator that rebuilds the plan itself and imports nothing from the solver. |
| 2:00 – 2:40 | How it works | One slide: door graph → exact hub search, cheapest of the ties → nodes by the doors → axis routing in separate lanes → independent validator scoring exactly as your slide 7. | "A cable can't go through a wall in our graph, because there is no edge through a wall." |
| 2:40 – 3:20 | Proof | `docs/figures/extra-hubs.svg`, then the results table. | "All 17,000 ResPlan plans. Every one that can be valid is: 16,556 of 16,556. 29,377 hubs against a lower bound of 23,893; a greedy baseline needs 31,046. Half the plans solve in 0.38 s on one process." |
| 3:20 – 3:50 | Try to break it | Edit mode: remove a bedroom's door, watch the hub count and "Why this many hubs?" change; Undo. Cut cable mode: cut a leg, "No device lost". | "A closed ring survives any single break; that's why the rules ask for it." |
| 3:50 – 4:30 | From prototype to service | Installer pack: cable schedule, loop resistance, bill of materials, commissioning sheet. | Roadmap: DXF and IFC import, multi-floor, fire-code detector placement, a hosted service. |
| 4:30 – 5:00 | Close | Title slide. | The team, thanks. |

## If something goes wrong

- **Server won't start or a solve hangs**: close it, open `out/16448.html` and carry on with the static viewer; the installer pack is `out/16448.installer.html`.
- **A judge's plan fails to solve**: say so plainly, show the diagnostics panel (it names the cause), and move to the next beat.
- **Everything fails**: play the backup video from the matching beat.

## Questions to expect

Rehearse against `docs/assumptions.md` (every rule reading and its default) and the numbers in `bench/results.md`. When unsure of a number, say where it comes from rather than guessing.
