# Cloud experiment access assessment

Created 02-11-2026-15-18-57 in Asia/Qyzylorda.

The latest steps 1–3 rerun passed with complete asset verification, three
full-strength baseline repetitions, all differential/control tools and 291 tests.
The project is ready for its registered bounded opportunity screen. The remaining
research gates are workstream selection, an improved generated artifact, fresh
candidate confirmation and verified release construction.

The measured workload-memory reserve is 11.17 GiB plus OS overhead. A 16 GB
x86 Linux VM is the initial cloud target. The supplied backend requires Linux
x86-64 and Python 3.13. Current scripts record absolute local paths, so cloud
deployment requires reviewed backend inventories and contract path relocation.

## Connection options

Google documents an official Compute Engine remote MCP server at
`https://compute.googleapis.com/mcp`, using Streamable HTTP and OAuth with IAM.
It provides VM, disk, snapshot and related infrastructure management. Its tool
reference supplies infrastructure operations. An experiment runner is still
needed for the project's Python commands.
[Compute Engine MCP](https://docs.cloud.google.com/compute/docs/use-compute-engine-mcp)

Codex supports remote Streamable HTTP MCP servers with authentication options.
This establishes a documented integration route. Google authentication, project
permissions and live client/server compatibility must be verified during setup.
[Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp)

The shortest execution route is an Ubuntu x86 Compute Engine VM accessed through
`gcloud compute ssh --tunnel-through-iap --command=...`. Codex can invoke that
CLI through its terminal tools, then inspect run status, retrieve logs and fetch
artifacts. IAP and OS Login require appropriate IAM and networking setup.
[Google SSH CLI](https://docs.cloud.google.com/sdk/gcloud/reference/compute/ssh)
[IAP connection setup](https://docs.cloud.google.com/compute/docs/connect/ssh-using-iap)

Google Batch is a second execution route. It accepts script or container jobs
through `gcloud batch jobs submit` and the Batch API. A job ID lets the client
monitor a run independently of the initiating shell connection. Use a pinned
Linux x86 environment, explicit resource limits and durable artifact storage.
[Batch jobs](https://docs.cloud.google.com/batch/docs/create-run-basic-job)

For initial bring-up, use SSH/IAP to validate one 16 GB x86 VM and its native
backend. For repeated experiments, use Batch with one immutable input/configuration
per job and retained logs/results. Compute Engine supports VM runtime limits for
bounded instances.
[Runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime)

## Current setup gaps

The session currently exposes no Google Cloud MCP connector. The Google Cloud
CLI is absent from the checked Windows and Ubuntu PATHs. Windows OpenSSH is
available. No Google project, region, authenticated principal, credit scope,
IAM access or VM connection has been verified. These are setup dependencies
before remote experiment execution can be demonstrated.

Investigation used current primary documentation and read-only local capability
checks. No cloud resource was provisioned. The public interface documentation
establishes the connection options, while account access remains a live setup check.

## Results publication

Fresh step-3 control records and the named JUnit result are retained under
`docs/evidence/rerun-20261102/`, alongside the top-level rerun summary. The large
archives and original inputs remain in ignored local storage, with their hashes
in the published receipts. This preserves reproducible identities and source
provenance while publishing the actual validation outcomes.

Simplicity review kept the recommended first integration to one VM and the
existing CLI entry points. Performance review reserved Batch for repeated jobs
and retained the measured two-core baseline until cloud profiling establishes
the benefit and memory cost of additional concurrency.
