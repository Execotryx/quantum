## ADDED Requirements

### Requirement: Any banked combination

Each release SHALL take, per task, the preferred banked member, or
otherwise the fallback member: v6 invsqrt, the routed DQI decoder
`d41de9ee…`, and the v6 chemistry family. A release SHALL NOT wait for a
member of another task.

#### Scenario: Chemistry banked, DQI not yet

- **WHEN** `chemistry-v8` is banked and no `dqi-v8` exists
- **THEN** the release uses `chemistry-v8` with the routed DQI decoder and v6 invsqrt

#### Scenario: DQI vendoring ends in `no_go`

- **WHEN** `vendor-public-inplace-dqi` records `no_go`
- **THEN** releases continue with the routed decoder as the DQI member

#### Scenario: Unbanked member

- **WHEN** a member hash is in neither a banked receipt nor the fallback list
- **THEN** packing stops

### Requirement: Immediate base release

Release `v8.0` SHALL be built from the three fallback members without
waiting for any vendored member.

#### Scenario: No vendored member banked

- **WHEN** no vendored member has been banked
- **THEN** `v8.0` is still registered, verified and uploaded

### Requirement: Release on improvement

A later release SHALL be made only when a banking event changes a chosen
member and raises the conservative projection by at least 2% over the last
released archive.

#### Scenario: Marginal improvement

- **WHEN** the new conservative projection is less than 2% above the last release
- **THEN** the release is recorded as `skipped`

### Requirement: Container chosen from the upload limit

The container mode SHALL be chosen from the recorded upload size limit:
`stored` when it fits, `deflate9` when only that fits or the limit is
unknown, and no upload when neither fits.

#### Scenario: Neither container fits

- **WHEN** the `deflate9` archive exceeds the recorded limit
- **THEN** the release stops with both sizes and the limit recorded

#### Scenario: Stored mode regression

- **WHEN** an existing release is packed in `stored` mode
- **THEN** its ZIP bytes equal the recorded archive

### Requirement: Pinned zlib build

A `deflate9` archive SHALL be packed only under the pinned zlib build.
Member hashes SHALL be the certification key.

#### Scenario: Different zlib at pack time

- **WHEN** the running zlib version differs from the pinned value
- **THEN** the packer refuses to write a `deflate9` archive

### Requirement: Single metric, single confirmation, one upload

Each release SHALL be scored once with the metric salt and once with the
confirmation salt, then uploaded once as `submission.zip` and reconciled
against its band.

#### Scenario: Score below band

- **WHEN** the public score is below the band widened by 1%
- **THEN** the shortfall and implied DQI failure count are recorded and no resubmission is made in this change
