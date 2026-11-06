## Why

The validated project needs repeatable operations from Codex, including long-running local checks and Google Cloud execution without embedding account credentials.

## What Changes

- Package a local Codex plugin with an MCP server and project operations skill.
- Delegate every project CLI action and step-3 tool to its existing implementation; retain provenance and acceptance gates.
- Persist asynchronous job registrations, process identities, logs, timeouts and cancellation results outside MCP sessions.
- Provide Google Compute Engine lifecycle, SSH/IAP execution, Batch job submission/monitoring and Cloud Storage transfers with explicit project configuration and dry-run previews.
- Supply credential-free configuration and cloud bootstrap code, install noninteractive dependencies, and test packaging, protocol, dispatch and job lifecycle.

## Capabilities

### New Capabilities
- `project-operations-plugin`: local and cloud orchestration from Codex.

## Impact

The plugin is additive. It does not change verifier algorithms, completed evidence or candidate gates. Account authentication and paid cloud execution remain deferred to the user's configured credentials and later run requests.
