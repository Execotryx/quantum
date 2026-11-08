# Metric reconciliation note

Record the old and observed notebook SHA-256 values and the source
revision, CLI version and UTC pull time. Retain both notebook versions
under the ignored run directory by hash.

## Diff and impact

Describe changes to input readers, benchmark definitions, coverage,
confidence procedures and cost aggregation. Identify each affected
control, its frozen ZIP and member hashes, and the comparison salt.

## Control replays

Link raw receipts for the old and observed versions. Compare coverage,
value and phase errors, component costs and the aggregate. Record the
reason for any discrepancy and how it changes release selection.

## Decision

Record the reviewer, date and whether the evidence supports changing the
pin. Record the reviewed contract change before preparing a ZIP against
the new metric.
