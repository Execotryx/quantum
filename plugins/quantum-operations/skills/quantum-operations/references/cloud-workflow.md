# Cloud workflow

1. Copy `configs/cloud.example.json` to ignored `configs/cloud.local.json` in the
   project. Fill project, region, zone, VM name, service account and bucket. Leave
   `gcloud` blank for PATH or the project-local SDK. On Windows the bundled SDK
   runs in the named WSL distribution; authenticate gcloud in that same runtime.
2. Verify billing/credit eligibility, APIs and IAM. The caller needs Compute
   permissions, IAP tunnel access and OS Login for SSH. Batch needs Job Editor and
   Service Account User. The VM/job service account needs Batch Agent where
   applicable, Logging Writer and appropriate access to the selected bucket.
   Enable Compute, Batch, Logging, Storage, IAP and OS Login APIs as applicable.
   Configure IAP SSH ingress and outbound network access (Cloud NAT/private
   Google access as required). A VM created here has no external IP.
3. Use an isolated deployment checkout. Run `cloud_relocation_plan` for its final
   Linux `remote_root`. Review the backend path-only changes and updated backend
   inventory hash, apply and commit the proposed files there. Reconcile the
   campaign configuration's `assets_root` too. Keep original evidence unchanged.
   Relocation is not native compatibility or full verifier acceptance evidence.
4. Commit the plugin before `cloud_snapshot`; it requires clean source. The tool
   writes a Git bundle, a selected-input tar and hash receipt under `runs/`.
   It includes the original input archive for baseline freezing and excludes
   account configuration, environments and installed tools. Use `additional_inputs`
   for explicitly selected candidate artifacts under runs/ or releases/. Upload the two
   archives using `cloud_storage` with unique object keys. Preserve the receipt.
5. Preview `cloud_vm(create)`, then execute when the resource is authorized.
   `cloud_vm_prepare` receives the object keys and exact archive hashes. It needs
   a fresh writable `remote_root` (default `/var/tmp/quantum`), Git, Python3, curl,
   sha256sum and gcloud on the guest. Ubuntu Google images normally supply the
   basic tooling; inspect failures rather than bypassing checks. Bootstrap
   verifies both transfers, restores the Git checkout, extracts safe inputs,
   installs pinned uv, syncs Python 3.13 with `--frozen`, then tests the native
   import. Run `contract.validate` on the VM before any acceptance claim.
6. Start `cloud_project_run` and retain its worker ID. Use `cloud_project_job`
   for status, bounded logs and cancellation. Poll the same ID after transient
   connection errors. Use `cloud_project_collect` once terminal to freeze/upload
   its receipts and output directory, then download through `cloud_storage`.
   Stop the VM when its authorized work ends; the runtime
   limit is an additional bound, and persistent disk/storage can remain billed.
7. For repeatable jobs, `cloud_batch_prepare` writes an inspectable one-task
   Batch config. Submit with `cloud_batch(submit)`, monitor with `describe`, and
   use the returned resource UID for `logs`. The job uploads receipts and outputs
   to `<prefix>/<job_id>/results.tar.gz` even when the delegated command fails.
   Download via `cloud_storage`; verify actual receipts before promoting a
   candidate. Deleting an active Batch job cancels it.

Batch bootstrap uses the same immutable source and input archives; keep operation
options relative to `remote_root`. Additional experiment configuration or candidate
artifacts belong in the committed source or a deliberately reviewed inputs package.
The initial measured budget assumes two CPUs; GPU execution is not supported by
the pinned native backend. Oracle Arm instances cannot run this x86 binary.
