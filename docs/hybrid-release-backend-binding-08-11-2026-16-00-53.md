# Release comparison across relocated backends

Candidate-v1 release comparison now accepts the original parent and
successor verifier requests as explicit supporting evidence when their
backend hashes differ. It rechecks the trusted parent certificate and
both request hashes, then compares the original inventory and records the
path-only review in the certificate. The backend hash in each receipt
remains intact.

The regression uses the saved v3 and v4 metric reports and requests.
Both proof files are required. Swapping a request fails its original
receipt hash check. The retained DQI and chemistry cost and coverage
checks still run against the supplied parent and successor evidence.

Component confirmation has a separate check. A protocol from a different
checkout must already pin its backend inventory. Certification rehashes
that inventory, checks the recorded backend identity and compares it
with the archive's original request. A changed or missing inventory
fails the gate. Candidate state, trusted lineage and external receipt
checks still apply.

The confirmation ledger rechecks the protocol identity when inheriting
a record. The release verifier also keeps fixed legacy coverage separate
from per-component counters, preserving the archived legacy parent
format. The regression reproduces the original legacy certificate.

[Supporting evidence format](operator-formats.md)
