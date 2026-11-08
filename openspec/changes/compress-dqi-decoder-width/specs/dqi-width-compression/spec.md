## ADDED Requirements

### Requirement: Proved in-place end state

An in-place decoder SHALL hold only states proved to be bijective
functions of the syndrome on every supported input. Its final
pre-scan state SHALL fit within the syndrome bank and the registered
workspace.

#### Scenario: Two syndromes collide

- **WHEN** an exhaustive small-field check finds two syndromes mapped to the same in-place state
- **THEN** the family is rejected at that stage and the collision is recorded

### Requirement: Small-field exhaustive prototypes

Each candidate family SHALL be prototyped classically over GF(2⁴) and
GF(2⁶) with every syndrome enumerated before any GF(4096) emission.

#### Scenario: A family passes the small fields

- **WHEN** a family restores every syndrome and applies the correct phase for every enumerated input
- **THEN** its full-size projection is computed with the measured routed-lane primitives

### Requirement: Linear phase scan correctness

A scan that uses `g = ω·Ψ mod σ` SHALL apply the mask phase as a
Clifford parity conditioned on the root flag and the classical mask,
and SHALL match the verifier's `popcount(e_j ∧ E_j)` parity.

#### Scenario: A dense mask

- **WHEN** a shot uses a mask with all bits set at a root position
- **THEN** the applied phase equals the parity of the recovered error value at that position

### Requirement: Admission and stop rule

A compressed decoder SHALL be admitted only if it costs at least 1.5× less
than the best admitted routed decoder. Work SHALL stop on 8 January 2027
unless a full-size candidate has passed the matched development pair.

#### Scenario: No candidate by the stop date

- **WHEN** no full-size candidate has passed the matched pair by 8 January 2027
- **THEN** the routed decoder remains the DQI component and the family records are archived
