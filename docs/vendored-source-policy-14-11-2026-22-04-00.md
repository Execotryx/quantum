# Vendored source policy

The repository now ships the canonical Apache 2.0 license and an attribution
notice. The provenance record binds the downloaded license by SHA-256 and byte
length. The source distribution and wheel both include the identical license
and notice bytes.

The policy requires originating license evidence, generating source and pinned
bytes for each admitted component. The integrity tests check the manifest
inventory and exclude names and hashes from the locked competition assets.
The policy describes when a regenerated member can advance to verification.

Ruff, Pyright, three focused tests, the frozen dependency lock and strict
OpenSpec validation passed. No public component was imported in this change.
