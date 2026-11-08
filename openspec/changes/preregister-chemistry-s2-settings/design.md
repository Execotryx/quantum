## Values

| Setting | Value | Source |
| --- | --- | --- |
| `penalty` | 1.0 | `optimize_s2` default, also used by the S2 CLI test |
| `offset_bound` | `B₀ = max(1.0, ⌈4 · m_ref⌉ / 2)` | `m_ref = max |H2_I_ref − W_ref.sum(axis=1)|` over the pinned reference `submission.npz` |
| `outer_iterations` | 4 | `promote-compressed-chemistry` |
| `evaluations` | 1,500 | same |
| `restore_evaluations` | 1,000 | same |
| `checkpoint_interval` | 250 | same |
| `wall_seconds` | 7,200 | same |

`B₀` is twice the largest reference offset magnitude, rounded up to a
multiple of 0.5, and never below 1.0. Record `m_ref`, the reference
offsets' mean and maximum magnitude, and `B₀` before writing any plan.

## Contingency (registered now, used at most once)

After restoration, compute `max |o|` over the restored offsets. If it is at
least `0.99 · B₀`, the bound was active. Write a second plan with
`offset_bound = 2 · B₀` and run S2 once more. That is the only rerun.
If the second run's restored offsets reach `0.99 · 2B₀`, record a
`budget_limited` S2 outcome and stop.

## Plan binding

`tools/chem_s2_settings.py write` emits the S2 plan JSON with:

- `lane`: id, vectors SHA-256, weights SHA-256, and checkpoint receipt SHA-256;
- `s1_decision`: path and SHA-256 of the lane's `go` decision;
- `target_pin`: path and SHA-256 from `chem_s2.py target`;
- `reference_offsets`: `m_ref`, the reference NPZ SHA-256 and `B₀`;
- `limits`: every value in the table;
- `contingency`: `{ "trigger": 0.99, "multiplier": 2, "max_reruns": 1 }`.

The plan's own SHA-256 is recorded in the change log before the run.
`chem_s2.py run` receives that hash as `expected_plan_hash`. The
shape-selection restoration in `select-compressed-chemistry-shape` reads
`offset_bound`, `penalty`, `restore_evaluations` and the floors from this
plan for every qualifying lane.
