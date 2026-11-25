# Vendored public source policy

Each component has a directory containing its upstream `LICENSE`, its
`NOTICE` when provided, a `SOURCE.json`, and byte-identical upstream files
under `src/`. If the origin explicitly declares Apache-2.0 without a license
file, copy the project's canonical license and add a `LICENSE.origin`
that quotes the declaration and gives its URL. Append the component, URL,
revision, authors, SPDX license and upstream notice to the root `NOTICE`.

`SOURCE.json` records `name`, `url`, `revision`, `authors`, `spdx`,
`retrieved_utc`, `files` (relative path, SHA-256 and byte length),
`published_outputs` (name and SHA-256), and `admission`. Hash all files
except the manifest itself. Under `admission`, record passing findings
for `explicit_license`, `generating_source`, `pinned_bytes`,
`no_competition_data` and `not_denylisted`. Each finding has a `passed`
boolean and an `evidence` string identifying the basis for the finding.
Record the originating license statement and actual generating files.

Admission requires an explicit Apache-2.0 license from the origin and
the source that generates the component. Published binary files can
serve as hash references. Exclude competition data, starter kit and
metric files, the yoyobar DQI lineage beginning `993c70386a3d`, and the
unlicensed jday96314 Schur continued-fraction decoder.

Keep changes and adapters in `src/qcompile/vendored/<component>/`.
Start derived files with the upstream URL, revision, path, date and a
one-line description of the modification.

The pipeline regenerates each admitted member twice in a clean
environment and applies the pinned metric and fresh confirmation gates.
Compare the rebuild to the hash published by the origin at the pinned
revision. Record a matching or differing OpenSpec hint when one exists.
If the origin publishes no hash, leave `published_outputs` empty and
use verification to qualify the rebuild. A differing circuit hash
excludes the candidate.

For a differing floating-point table, verify the regenerated and
published tables with the same loaders. If both pass and their λ_eff
values agree within 1×10⁻⁶ relative, record both hashes and select the
published bytes as `equivalent`. If the rebuild passes and the two
tables are not equivalent, select the rebuild as `divergent_rebuild`.
Otherwise exclude the table.
