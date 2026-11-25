#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <limits.h>

/* Only changes libc temporary-file placement. Circuit serialization, hashing,
   simulation, shot generation, and the official verifier are unchanged. */
static FILE *dqi_tmpfile(void) {
    const char *dir = getenv("DQI_NATIVE_TMPDIR");
    if (!dir || !*dir) { errno = EINVAL; return NULL; }
    char path[PATH_MAX];
    int n = snprintf(path, sizeof(path), "%s/kickmix-XXXXXX", dir);
    if (n < 0 || n >= (int)sizeof(path)) { errno = ENAMETOOLONG; return NULL; }
    int fd = mkstemp(path);
    if (fd < 0) return NULL;
    unlink(path);
    FILE *stream = fdopen(fd, "w+b");
    if (!stream) { int saved = errno; close(fd); errno = saved; }
    return stream;
}
FILE *tmpfile(void) { return dqi_tmpfile(); }
FILE *tmpfile64(void) { return dqi_tmpfile(); }
