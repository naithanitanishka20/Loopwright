# Batch report

Plans: 1000 · zone rule: strict · caps: 100 m², 5 nodes

| Status | Plans |
|---|---|
| valid | 939 |
| invalid | 31 |
| infeasible | 30 |

Valid on feasible plans: 939 of 970 (96.8%)
Hubs: 1839 against a lower bound of 1496 and greedy's 1951
Runtime per plan: p50 1.33 s, p95 5.42 s

| Cause | Plans | Examples |
|---|---|---|
| infeasible/V03/ROOM_OVER_CAP | 30 | 3827, 8959, 5191 |
| invalid/V10/ROUTER_FALLBACK | 22 | 11160, 407696, 742848 |
| invalid/V10/EXTRA_HUB | 4 | 624783, 557925, 3328 |
| invalid/V12/ROUTER_FALLBACK | 1 | 384263 |
| invalid/V05/- | 1 | 15258 |
| invalid/V12/EXTRA_HUB | 1 | 682851 |
| invalid/V10/NO_LINK | 1 | 10216 |
| invalid/V05/EXTRA_HUB | 1 | 11912 |
