# Local cloud configuration import

Created 06-11-2026-13-15-10 in Asia/Qyzylorda.

Imported the nine deployment settings emitted by the Cloud Shell provisioner
into the ignored local plugin configuration. Validated that all fields are
nonempty and that the project, region, zone and service account agree. Kept the
deployment values out of tracked files. The installed plugin reads the config
on each operation, so this import requires no plugin rebuild.
