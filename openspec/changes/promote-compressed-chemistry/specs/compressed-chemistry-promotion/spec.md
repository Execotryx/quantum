## ADDED Requirements

### Requirement: Single fixed-limit pipeline

S2, S3 and the loader ranking SHALL each run once with the limits
registered in this change, on the factorization handed off by the
alternating-projection fit.

#### Scenario: S2 finds no eligible checkpoint

- **WHEN** S2 ends without a checkpoint that passes every project margin
- **THEN** the change records the outcome and stops without a second S2 run

### Requirement: Highest passing precision

The ladder SHALL stop at the first failing precision. Loader synthesis
SHALL use the last passing precision.

#### Scenario: 8-bit words fail

- **WHEN** the 8-bit step fails a margin and the 9-bit step passed
- **THEN** the loader ranking uses 9-bit words

### Requirement: Full verification of the new family

The selected ANGLE family and NPZ SHALL be built twice identically and
pass the complete metric at `(76 + R·B) · 64` shots and a fresh one-use
confirmation.

#### Scenario: Two builds differ

- **WHEN** the two builds produce different bytes
- **THEN** promotion stops until the difference is explained and removed

### Requirement: Promotion gate

The new chemistry component SHALL cost at most 1.624×10⁹ on the complete
metric.

#### Scenario: The family meets the gate

- **WHEN** the verified chemistry cost is at or below the gate
- **THEN** it becomes the chemistry member of the next paired archive
