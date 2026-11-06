## ADDED Requirements

### Requirement: Installable credential-free plugin
The plugin SHALL provide a supported Codex manifest, MCP configuration, discoverable skill, frozen dependencies and empty account configuration. Startup SHALL work without cloud credentials.

#### Scenario: Fresh local installation
- **WHEN** the frozen plugin dependencies are installed and the server starts
- **THEN** an MCP client can initialize, list tools and inspect project readiness without cloud authentication

### Requirement: Preserve project operations and gates
The plugin SHALL delegate all existing CLI operations and step-3 checks without inventing verification success, editing evidence or bypassing candidate state gates.

#### Scenario: Invalid command options
- **WHEN** an unknown operation or unsupported option is requested
- **THEN** the request fails before launching a job

### Requirement: Durable experiment lifecycle
Jobs SHALL retain immutable registrations, streamed logs, exit codes and process identities. Polling and cancellation SHALL validate the actual process, and subprocess trees SHALL terminate on timeout or cancellation.

#### Scenario: Client reconnects
- **WHEN** the MCP session closes while an experiment is running
- **THEN** a later session can inspect the same job without starting another experiment

### Requirement: Google Cloud execution
The plugin SHALL provide previewable Compute Engine lifecycle and SSH/IAP operations, Batch execution and monitoring, and artifact upload/download through the installed Google Cloud CLI. It SHALL require explicit project/location configuration and preserve separate authentication outside tool output.

#### Scenario: Credentials are not configured
- **WHEN** a cloud operation is previewed
- **THEN** its required configuration is reported and no resource is provisioned

#### Scenario: Native verification is requested remotely
- **WHEN** cloud bootstrap prepares the project
- **THEN** it uses Linux x86-64 Python 3.13 with frozen dependencies and requires explicit backend path reconciliation before claiming full readiness
