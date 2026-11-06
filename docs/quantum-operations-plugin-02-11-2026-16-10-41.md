# Project operations plugin

Created 02-11-2026-16-10-41 in Asia/Qyzylorda.

The requested Codex plugin is implemented under `plugins/quantum-operations`,
with a repository-local marketplace, supported Codex manifest, stdio MCP server,
workflow skill and frozen independent dependency lock. Its 29 catalog entries
cover every existing project CLI action, all eleven step-3 scripts and three
quality checks. No scientific dependency or evaluator pin was changed.

The plugin supervises Linux jobs independently of MCP sessions, retains immutable
registrations and streaming logs, records exit status, checks boot/PID start-time
identities, and terminates observed process descendants on cancellation/timeout.
It supports bounded log/evidence reads and terminal output exports. Existing
candidate and release gate checks remain inside the authoritative CLI.

Google Cloud code supports previewable VM lifecycle, SSH/IAP bootstrap and jobs,
Batch configuration/submission/status/logs/deletion, selected Cloud Storage
transfers and terminal VM result collection. Clean-source Git bundles and
allowlisted input archives retain SHA-256 receipts, including the original input
archive needed by baseline freezing. Backend relocation produces review files
without changing existing pins or evidence. Account settings remain empty in the
template and its ignored local copy. Authentication uses the user's gcloud store;
no token, key or credential file was created or populated.

## Dependencies and installation

- Installed the frozen MCP bridge dependencies (MCP SDK 1.30.0 maintenance line)
  and development tools in isolated Windows and Ubuntu environments under vendor/.
- Installed official Google Cloud SDK 591.0.0 under `vendor/google-cloud-sdk`.
  The bridge discovers this SDK and invokes it in Ubuntu WSL on Windows.
- Existing uv, Git, Node, OpenSSH and Ubuntu Python runtimes were reused.
- Codex accepted and installed `quantum-operations@quantum-local` in an isolated
  profile and the normal user profile. Generated test caches were removed from
  the source package after a cache ACL prevented the first normal-profile copy.
- The exact installed MCP manifest started successfully, exposed all 17 tools,
  and launched actual project contract validation through WSL. Its terminal
  receipt reports `ready`, zero blockers and exit code zero.

## Validation

- Linux Python 3.13: all 17 plugin tests pass, including actual stdio initialization,
  parser/catalog parity for every CLI command, process failure status, detached
  descendants, timeouts, cancellation, stale identities, MCP disconnect/reconnect,
  snapshot restore, account-file exclusion, output export, relocation preservation,
  cloud previews and transfer-hash rejection by the actual bootstrap shell.
- Windows Python 3.12: 10 tests pass; seven Linux-only checks skip intentionally.
- Existing project suite: all 291 tests pass after adding the plugin.
- Pyright reports zero errors for every new Python module/test. Ruff lint and
  format checks pass. Bootstrap shell syntax and strict OpenSpec validation pass.
- The installed SDK's command help confirms VM runtime-limit and storage
  no-overwrite flags. No authenticated cloud call or paid resource was created.
- A dedicated Ubuntu CI job installs both frozen environments and runs plugin
  checks, preserving the existing independent scientific CI jobs.

Raw local JUnit records are `runs/plugin-tests-linux.xml`,
`runs/plugin-tests-windows.xml` and `runs/plugin-project-regression.xml`.
The test-profile install and source package are reproducible from the plugin
manifest and lock. Live Google authentication, IAM, project quotas, credit scope,
network access and actual cloud execution remain account-dependent setup checks.
Published validation receipts are retained under `docs/evidence/plugin-20261102/`.

## Simplicity review

The first review removed the need for another cloud SDK dependency or a second
verification implementation: the plugin uses the installed gcloud CLI and the
project's existing commands. Shared bootstrap generation handles both VM and Batch
paths. Authentication is delegated to gcloud instead of adding unused token fields.
The second review found no further justified abstraction or duplicate workflow.

## Performance review

Logs are written directly to disk and read in bounded byte pages. Archives and
hashes stream files, avoiding whole-artifact memory copies. Process-tree traversal
uses an adjacency map instead of repeatedly scanning the complete PID table.
Development environments were moved out of the plugin source to avoid copying
them into every installation. The final review found no further measured need
for optimization. Process-tree sampling retains a documented enumeration race;
it is not a privileged cgroup boundary. Cloud plans use serial two-core execution
with explicit memory and duration bounds until new measurements justify changes.

The pre-existing deletion of `vendor/README.md` was preserved. No Git commit or
publication was performed for this code-only request.
