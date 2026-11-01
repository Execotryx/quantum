# Baseline campaign runtime recovery

Created: 02-11-2026-02-05-36 (Asia/Qyzylorda).

The initial step-2 campaign from committed source `4ff6c1e` stopped during
DQI after successful chemistry and inverse-square-root component receipts.
Linux kernel evidence confirms a global OOM kill. The initial WSL allocation
was approximately 7.6 GiB RAM and 2 GiB swap. This attempt does not establish
complete baseline acceptance and is retained under `runs/baseline-campaign-v1`.

An 8 GiB disk-backed temporary swap file was created at
`/var/tmp/qcompile-baseline-step2.swap`; no fstab or persistent WSL settings
were changed. `/tmp` is RAM-backed on this system and could not host the file.

Two subsequent attempts stopped during low-memory copying, including an
ordinary-user foreground TTY attempt. Investigation found `init.scope` in
`ActiveState=deactivating`, `Result=oom-kill`, `OOMPolicy=stop`, with
`memory.events` retaining `oom_kill 1` across restarted distro namespaces.
The kernel boot identity remained unchanged. Thus a live foreground terminal
alone did not resolve the runtime fault. Both retries remain incomplete, with
their logs and interruption records retained separately.

Both registered distros (`Ubuntu`, `kali-linux`) were reported stopped and all
campaign launch handles were terminal before resetting the idle WSL VM with
`wsl --shutdown`. The next launch must verify a new kernel boot identity,
cleared OOM counters, active init scope, and active temporary swap before retry.
This recovery changes the execution environment, not the verifier, source,
original artifacts, full-strength coverage, salts, or acceptance requirements.

The completed campaign's host memory/swap inventory and sampled PSS, RSS and
proportional swap will determine planning budgets. The interrupted attempts
must remain excluded from normalization/repeatability conclusions.

Simplicity review: retained separate attempts and used a runtime reset rather
than adding verifier retry/resume behavior or changing acceptance gates.
Performance review: additional swap provides capacity at a potential I/O cost;
measure the actual successful runtime rather than extrapolating earlier results.

Completion update: the VM reset produced a new kernel boot identity and cleared
all init-scope OOM counters; `ActiveState=active` and `Result=success` were verified.
The complete A1/A2/B1 retry then passed, followed by bundle construction and the
independent completion audit. Temporary swap had zero used bytes after those jobs
finished; it was deactivated and its exact task-created file removed. The original
2 GiB swap remained active. See the
[completion report](baseline-completion-02-11-2026-03-02-06.md) for measured results.
