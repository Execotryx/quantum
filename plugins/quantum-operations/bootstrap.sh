# Runs as the VM/Batch job principal; no embedded account credentials.
set -eu
test "$(uname -m)" = x86_64
: "${QUANTUM_ROOT:?absolute destination required}"
: "${QUANTUM_SOURCE_URI:?source Git bundle URI required}"
: "${QUANTUM_SOURCE_SHA256:?source digest required}"
: "${QUANTUM_INPUTS_URI:?inputs tar URI required}"
: "${QUANTUM_INPUTS_SHA256:?inputs digest required}"
test ! -e "$QUANTUM_ROOT"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
gcloud storage cp "$QUANTUM_SOURCE_URI" "$stage/source.bundle"
gcloud storage cp "$QUANTUM_INPUTS_URI" "$stage/inputs.tar.gz"
printf '%s  %s\n' "$QUANTUM_SOURCE_SHA256" "$stage/source.bundle" | sha256sum -c -
printf '%s  %s\n' "$QUANTUM_INPUTS_SHA256" "$stage/inputs.tar.gz" | sha256sum -c -
git clone "$stage/source.bundle" "$QUANTUM_ROOT"
cd "$QUANTUM_ROOT"
# Python's data filter rejects traversal and unsafe links in transferred inputs.
python3 -c 'import sys,tarfile; tarfile.open(sys.argv[1]).extractall(".",filter="data")' "$stage/inputs.tar.gz"
if ! command -v uv >/dev/null 2>&1; then
    # Pinned installer version; installed for this job user only.
    curl --fail --location --silent --show-error https://astral.sh/uv/0.11.32/install.sh -o "$stage/install-uv.sh"
    UV_NO_MODIFY_PATH=1 sh "$stage/install-uv.sh"
fi
export PATH="$HOME/.local/bin:$PATH"
export UV_PROJECT_ENVIRONMENT=vendor/linux-env
uv sync --frozen --python 3.13
# Native loadability is separate from mathematical/full verifier acceptance.
vendor/linux-env/bin/python -c 'import sys; sys.path.insert(0,"vendor/official/kickmix"); import kickmix; print("native import passed")'
