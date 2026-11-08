# Paired archive backend request review

The v3 and v4 verification receipts preserve different backend identities
because each run used a different source checkout path. The original
[v3 request](evidence/advance-hybrid-20261108/archive/request.json) and
[v4 request](evidence/invsqrt-roadmap-archive-20261108/request.json) now
accompany the receipts. Their digests are the values already recorded by
the verifier.

`tools/hybrid_certification.py review-backend` compares the two inventories
after checking each request against its own receipt, environment, artifact
hashes, contract, tier and seed. The [recorded comparison](evidence/invsqrt-roadmap-archive-20261108/backend-pair.json)
finds one changed field, `project_root`. The metric notebook, verifier
sources, native binary inventory and counter mappings match.

The review binds the saved records and compares their recorded backend
pins. It leaves the original receipt identities intact. Release
certification still requires trusted parent lineage and accepted
component confirmation records.
