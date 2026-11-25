## ADDED Requirements

### Requirement: Confirm the native extraction fault on frozen inputs

The diagnostic SHALL bind the original circuit bytes, source inventory,
verifier, and captured batches. It SHALL compare native words before synthesis
with a D4-geometry rational oracle and distinguish finite, terminated, and
nonterminal pole states.

#### Scenario: Original failure and control replay

- **WHEN** the instrumented rebuild matches the banked circuit hash and the original batches are replayed
- **THEN** the diagnostic records the first observed upstream mismatch or records that the hypothesized mismatch could not be reproduced

### Requirement: Preserve rational semantics and reversible cleanup at poles

The repair SHALL continue the correct rational recurrence across reachable
intermediate and local poles. It SHALL preserve the supported finite and
terminating paths and restore the syndrome, mask and workspace with the
correct phase.

#### Scenario: Nonterminal pole in a doubled node

- **WHEN** a zero denominator occurs with a nonzero residual at an intermediate jet or a local inverse
- **THEN** the repaired extraction and synthesis preserve the rational continuation and emit a polynomial containing the true error support

#### Scenario: Legitimate rational termination

- **WHEN** the residual is identically zero
- **THEN** the circuit preserves the terminating representation and uncomputes its temporary state without a wrong phase

### Requirement: Verify the frozen repaired decoder

The cloud campaign SHALL bind two byte-identical builds, verify both circuits
on the captured inputs, and record full official outcomes and cost on eight
fresh salts. It SHALL retain original and candidate evidence separately.

#### Scenario: Candidate has correct fixed phases and passes full verification

- **WHEN** the repaired candidate clears every captured failure, preserves the passing controls and passes all eight official draws
- **THEN** the report records any remaining statistical failures, declared width, mean Toffolis and pooled cost alongside banked D4

#### Scenario: Repair introduces a regression

- **WHEN** the candidate causes a new failure in a matched captured batch or fails a full verifier draw
- **THEN** the report preserves the failed evidence and leaves banked D4 unchanged
