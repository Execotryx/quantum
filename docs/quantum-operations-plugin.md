# Quantum Operations plugin

The local Codex plugin lives in `plugins/quantum-operations`. It delegates the
existing project CLI and controls, supervises durable Linux jobs, and provides
Google Cloud VM, SSH/IAP, Batch and artifact operations. Credentials are absent
from the plugin and template. The account configuration file is ignored.

## Install and configure

Prerequisites: uv, Python 3.12+ for the MCP bridge, and the project's frozen Linux
Python 3.13 environment for experiments. Windows uses Ubuntu WSL automatically.

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) 'vendor/plugin-windows-env'
uv sync --project plugins/quantum-operations --frozen
Remove-Item Env:UV_PROJECT_ENVIRONMENT
codex plugin marketplace add E:/sources/python/quantum
codex plugin add quantum-operations@quantum-local
```

The repository marketplace discovers the plugin. Restart Codex after installing
or changing plugin files. No Google login is required to start the server or
use local tools. A separate environment keeps MCP dependencies out of the frozen
scientific dependency lock.
Keep development environments outside the source plugin directory to avoid
copying them into installation caches. The installed MCP manifest manages its
own bridge environment on first startup.

Copy `configs/cloud.example.json` to `configs/cloud.local.json` and fill cloud
resource choices when ready. `gcloud` can stay empty: the plugin uses PATH or the
ignored `vendor/google-cloud-sdk/bin/gcloud` installation. Authenticate using
`gcloud auth login` in the OS runtime that executes that CLI. No token is needed
in the JSON file. Do not commit credential files.

For cloud setup, follow the plugin skill's
[cloud workflow](../plugins/quantum-operations/skills/quantum-operations/references/cloud-workflow.md).
Live authentication, IAM, quota, billing credits and networking require account
access and are not established by offline tests.

## Provision the VM environment from Cloud Shell

Upload `tools/provision-quantum-cloud.sh` to Google Cloud Console's Cloud Shell.
Use a dedicated project and replace the example project ID, zone, and globally
unique bucket name. Run the first command to preview the changes.

```bash
bash provision-quantum-cloud.sh my-quantum-project us-central1-a my-quantum-artifacts
bash provision-quantum-cloud.sh my-quantum-project us-central1-a my-quantum-artifacts --apply > cloud.local.json
```

The active Cloud Shell user needs permission to manage APIs, networking, IAM,
storage and Compute Engine in the target project. Use a billed project or set
`BILLING_ACCOUNT` to create/link a project with the appropriate billing and
project creation permissions. The script uses fixed names and reuses resources
by name on reruns. Use a dedicated project and reserve those names for this
script. Existing resources are assumed to match the original configuration.

Copy the generated JSON to the local project's ignored `configs/cloud.local.json`.
Use the same Google user when signing in to the CLI used by Codex. The IAP grant
applies to SSH on port 22 within the project. The OS Login grant applies to the
worker VM. Check guest tools before running `cloud_vm_prepare`, which handles
source and input transfer and the frozen Python setup. The VM stops after one
hour. Cloud NAT, persistent disks and bucket storage can continue to incur charges.

## Tools and evidence

- `project_catalog`, `project_status`: command coverage and readiness.
- `project_run`, `project_job_status`, `project_job_logs`, `project_job_cancel`:
  preview or supervise existing CLI actions and step-3 controls.
- `project_evidence`: bounded evidence pages; no arbitrary file reads.
- `cloud_relocation_plan`, `cloud_snapshot`: reviewable path migration and
  clean-source, hash-inventoried transfer archives.
- `cloud_vm`, `cloud_vm_prepare`, `cloud_project_run`, `cloud_project_job`:
  VM lifecycle, bootstrap and durable experiments through IAP.
- `cloud_project_collect`: freeze terminal VM receipts/outputs and upload the
  archive for download through `cloud_storage`.
- `cloud_batch_prepare`, `cloud_batch`, `cloud_storage`: batch job scripts,
  monitoring and selected artifact transfers.

Cloud tools preview by default. Local jobs also require `execute=true` to start.
Registrations and logs are retained in `runs/plugin-jobs/<id>/`; process identity
binds Linux boot ID and PID start time, so stale receipts cannot cancel reused
PIDs. Timeout/cancellation also targets descendants that create new sessions.
Jobs survive an MCP client disconnect; machine shutdown still interrupts them.
Process-tree termination uses Linux `/proc` observations and retains its inherent
enumeration race; it is not a privileged cgroup resource boundary.

Step-3 controls use existing output paths. Run them in a separate checkout to
retain prior evidence. A clean source snapshot contains committed code only.
Review/apply relocation proposals in that deployment checkout before committing
and transferring it. Native load checks and successful jobs do not replace full
coverage, primitive controls, fresh confirmation or release acceptance gates.

## Development checks

```bash
UV_PROJECT_ENVIRONMENT=vendor/plugin-linux-env uv sync --project plugins/quantum-operations --frozen --python 3.13
vendor/plugin-linux-env/bin/python -m pytest -c plugins/quantum-operations/pyproject.toml plugins/quantum-operations/tests
vendor/plugin-linux-env/bin/pyright --pythonpath vendor/plugin-linux-env/bin/python plugins/quantum-operations
vendor/plugin-linux-env/bin/ruff check plugins/quantum-operations
```

Authoritative packaging references:
[Codex plugin packages](https://developers.openai.com/plugins/build/plugins),
[local MCP packages](https://developers.openai.com/plugins/deploy/desktop-only),
[MCP Python SDK maintenance line](https://py.sdk.modelcontextprotocol.io/v1/).
