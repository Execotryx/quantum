## 1. Licence file (distinct file)

- [x] 1.1 Create the root `LICENSE` with the complete, unmodified Apache License 2.0 text from apache.org, or the verified fallback copy.
- [x] 1.2 Record its SHA-256, byte length, source and retrieval time in `third_party/licenses.json`.
- [x] 1.3 Add `license = "Apache-2.0"` and `license-files = ["LICENSE", "NOTICE"]` to `pyproject.toml`. Confirm `uv build` includes both files.

## 2. Notice and layout

- [x] 2.1 Create the root `NOTICE` with the project header.
- [x] 2.2 Create `third_party/README.md` describing the layout, admission checks, denylist and regeneration rule.

## 3. Policy

- [x] 3.1 Replace the independent-generation-only line in `AGENTS.md`. Add the same rule to `CLAUDE.md` and a licensing section to `README.md`.

## 4. Test

- [x] 4.1 Add `tests/test_third_party.py` with the licence, provenance, notice and competition-data checks.
- [x] 4.2 Ruff, Pyright, pytest and strict OpenSpec validation. Dated change log.
