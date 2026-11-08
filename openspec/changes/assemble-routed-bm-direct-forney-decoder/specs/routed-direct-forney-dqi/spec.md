## ADDED Requirements

### Requirement: History depth fixed by measurement

The history depth `h` SHALL be the smallest value in {1, 2, 3} whose
classical overflow rate on 10,000,000 sampled inputs is at most `1e-6`,
or 3 if none qualifies. The change SHALL stop if any sampled locator degree
exceeds `min(r, 35)`.

#### Scenario: One entry suffices

- **WHEN** inputs needing two or more retained discrepancies occur at a rate of `1e-6` or less
- **THEN** `h = 1` is registered before any circuit emission

### Requirement: Circular template with classical offset

The template SHALL occupy 36 physical words whose coefficient mapping
shifts by a classical offset each round, with no data movement for the
shift. A zero-discrepancy round SHALL relabel the template, leave the
locator unchanged and increment the counter, even when the wrapped
constant word is nonzero.

#### Scenario: A zero-discrepancy round with a wrapped word

- **WHEN** a round has `Δ = 0` and a nonzero wrapped `T_0`
- **THEN** the locator and template words equal their relabeled inputs, the counter equals `d + 1`, and scratch is zero

### Requirement: Tagged bounded history

History SHALL follow `specify-dqi-history-overflow`: tagged push and pop,
value-only flag clearing, and a never-decremented overflow count that
makes an overflowed shot a counted verifier error.

#### Scenario: History overflows

- **WHEN** a fixture forces `h + 1` retained discrepancies
- **THEN** the overflow count is nonzero at the end, the verifier reports an error for that input, and all other fixtures pass

### Requirement: Scaled in-place evaluator

The evaluator SHALL overwrite `S1..S35` with `ω = σ·S mod z³⁵` for a
locator with any nonzero constant, and its reverse SHALL restore the
syndromes exactly.

#### Scenario: A rescaled locator

- **WHEN** the locator constant is any nonzero field element
- **THEN** the in-place `ω` equals the classical evaluator of the same scaled locator, and the reverse restores every syndrome

### Requirement: Decoder admission

The assembled `(4095, 70)` decoder SHALL show zero value and phase errors
on the matched 2,560-shot pair. Its cost, priced at two more failures than
the worst of five salts, SHALL be at most `1.2220×10¹³`.

#### Scenario: The decoder meets the gate

- **WHEN** the matched pair is clean and the priced cost is within the gate
- **THEN** the frozen bytes go to the full verifier and fresh confirmation
