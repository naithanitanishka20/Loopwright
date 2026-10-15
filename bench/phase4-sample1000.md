# Batch report

Plans: 1000 · zone rule: strict · caps: 100 m², 5 nodes

| Status | Plans |
|---|---|
| valid | 949 |
| infeasible | 30 |
| invalid | 21 |

Valid on feasible plans: 949 of 970 (97.8%)
Hubs: 1849 against a lower bound of 1496 and greedy's 1959
Runtime per plan: p50 1.01 s, p95 4.58 s

| Cause | Plans | Examples |
|---|---|---|
| infeasible/V03/ROOM_OVER_CAP | 30 | 3827, 8959, 5191 |
| invalid/V10/ROUTER_FALLBACK | 14 | 407696, 742848, 1180 |
| invalid/V10/EXTRA_HUB | 2 | 624783, 557925 |
| invalid/V12/ROUTER_FALLBACK | 1 | 384263 |
| invalid/V05/- | 1 | 15258 |
| invalid/V12/EXTRA_HUB | 1 | 682851 |
| invalid/V10/NO_LINK | 1 | 10216 |
| invalid/V05/EXTRA_HUB | 1 | 11912 |
