# Cloud Shell provisioning

Created 06-11-2026-02-23-12 in Asia/Qyzylorda.

Added a Bash entry point for the VM deployment from Cloud Shell. It provisions
the required APIs, dedicated VPC and subnet, IAP firewall rule, Cloud NAT,
private bucket, workload identity and bounded VM. It emits JSON for the Codex
plugin and supports optional project creation and billing linkage. The VM uses
the existing plugin bootstrap for project files and the locked environment.

The simplicity review kept one script and one deployment profile. It replaced
an unsupported Compute Engine IAP CLI command with the documented project IAM
binding restricted to SSH. The performance review kept one inventory query per
resource type, with no network queries in preview mode. Reruns reuse names in a
dedicated project and stop on failed inventory queries.

Verified Bash syntax and exercised preview, fresh creation, rerun and inventory
failure with a mocked gcloud CLI. Live IAM, billing and provisioning still need
verification when the operator applies the script in Cloud Shell.
