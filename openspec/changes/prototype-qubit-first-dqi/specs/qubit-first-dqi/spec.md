## ADDED Requirements

### Requirement: Runtime-mask phase and reversible cleanup

The DQI prototype SHALL restore the original syndromes, clear scratch
and apply the correct sign for the trajectory's classical mask in
the pinned field and indexing convention.

#### Scenario: Same syndrome and different mask

- **WHEN** two trajectories have identical syndromes but masks with different target parities
- **THEN** the native circuit produces the two expected signs and restores all public and scratch qubits

### Requirement: Measured width and full DQI cost

A candidate SHALL have an evidenced register schedule and use measured
declared width, mean Toffolis and actual disjoint failure counts for
promotion under the pinned confidence penalty.

#### Scenario: Small development sample looks favorable

- **WHEN** a candidate improves on the matched reduced-strength control
- **THEN** it may advance to a full run and its development score is not treated as a full measured improvement

#### Scenario: Narrow layout cannot prove cleanup

- **WHEN** an optimized path loses state needed to reverse the decoder
- **THEN** it is rejected regardless of its projected qubit count
