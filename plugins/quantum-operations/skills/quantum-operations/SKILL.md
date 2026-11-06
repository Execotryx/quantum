---
name: quantum-operations
description: Operate this quantum compilation project from Codex: inspect readiness, run contract and mathematical checks, supervise baseline/candidate/release jobs, and prepare or execute Google Cloud experiments.
---

Use the bundled `quantum-operations` MCP tools with an explicit absolute project
`root`. Start with `project_status` and `project_catalog`; pass catalog options
with hyphens, such as `seed-policy`. Runtime configuration is the project's
ignored `configs/cloud.local.json`, copied from `configs/cloud.example.json`.
Authentication is user-managed through gcloud. Never ask for tokens in chat.

## Local experiments

`project_run` previews by default. Execute an authorized operation with
`execute=true`, keep its `job_id`, poll `project_job_status`, and page logs using
`next_offset`. MCP disconnects do not cancel jobs. A polling timeout is not a
failed experiment. `interrupted` means the recorded process identity is absent
without a terminal receipt; inspect retained logs before deciding on a new run.
Use `project_job_cancel` only when cancellation is requested or part of the
authorized experiment policy.

The catalog includes every qcompile CLI action, all eleven step-3 tools and
quality checks. The existing CLI enforces candidate and release gates. Successful
process exit is not evidence of improvement or overall acceptance: inspect the
actual receipts, coverage, costs and supporting evidence. Read `docs/operator-formats.md`
for argument schemas. Use OpenSpec for implementation/experiment plans.

Step-2 campaigns need clean committed Linux source and frozen dependencies.
Preregister serial full-strength A,A,B; keep candidate confirmation salts fresh.
Step-3 tools write their established evidence paths, so use a separate checkout
to preserve prior campaigns. Native verification needs x86-64 Linux and Python
3.13. The measured memory planning reserve is 11.17 GiB plus OS overhead; start
with 16 GB RAM and profile before increasing concurrency.

## Google Cloud

Read [cloud workflow](references/cloud-workflow.md) when preparing deployment or
operating a cloud experiment. Tools preview cloud commands unless `execute=true`.
Creation and execution need authorization for the actual resource/job; plugin
installation alone does not authorize cloud spending. Status and logs can be
queried for an existing authorized job without asking again. No token belongs in
a tool argument, command line, manifest, source bundle or result archive.

Use the normal GitHub connector or Git CLI for source review/publication; preserve
unrelated worktree changes. The plugin does not silently commit, push or publish
research artifacts. The [operator guide](../../../../docs/quantum-operations-plugin.md)
in the source checkout describes installation and configuration; in a cached
plugin installation resolve that document from the explicit project root.
