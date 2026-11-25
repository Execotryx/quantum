## 1. `LICENSE`: the Apache License 2.0 text, as a distinct file

1. Create `LICENSE` at the repository root. Its whole content is the Apache
   License, Version 2.0, exactly as published at
   `https://www.apache.org/licenses/LICENSE-2.0.txt`:
   - from the title `Apache License` / `Version 2.0, January 2004`,
   - through `END OF TERMS AND CONDITIONS`,
   - and the `APPENDIX: How to apply the Apache License to your work.`
     section with its boilerplate.

   No project text is inserted, and the appendix placeholders
   (`[yyyy] [name of copyright owner]`) stay unfilled. The copyright line goes
   in `NOTICE`.
2. Source of the bytes:
   - **Primary:** download the URL above.
   - **Fallback:** if the URL is unreachable from the build environment, copy
     the licence file shipped inside an installed Apache-2.0 distribution, for
     example a `*.dist-info/licenses/LICENSE` whose first line is
     `Apache License`.
   - The fallback must match the canonical text from title to appendix end,
     after normalizing line endings to `\n` and stripping trailing spaces.
     Check it against the canonical text the first time a networked
     environment is available.
3. Line endings are `\n`, and the file is UTF-8 without a BOM.
4. Record in `third_party/licenses.json`:
   - the file's SHA-256;
   - the byte length;
   - the source used (URL or distribution name and version);
   - the retrieval UTC timestamp.
5. Add to `pyproject.toml` under `[project]`:
   `license = "Apache-2.0"` and `license-files = ["LICENSE", "NOTICE"]`.
6. The `LICENSE` file is never edited by later changes. A licence update is
   its own change.

## 2. `NOTICE`

The root `NOTICE` starts with:

```
qcompile
Copyright 2026 Viktoriya (Execotryx) and contributors.
Licensed under the Apache License, Version 2.0 (see LICENSE).

This product includes third-party software listed below.
```

Each vendored component then appends one block: component name, upstream
URL, revision or dataset version, authors, licence (SPDX `Apache-2.0`), and
the upstream `NOTICE` content verbatim when one exists (Apache §4(d)).

## 3. `third_party/<component>/` layout

| File | Content |
| --- | --- |
| `LICENSE` | Upstream licence file, verbatim. If upstream states Apache-2.0 without a file, a copy of the root `LICENSE` plus `LICENSE.origin` quoting the upstream statement and its URL |
| `NOTICE` | Upstream `NOTICE` verbatim, if present |
| `SOURCE.json` | `name`, `url`, `revision` (commit SHA or dataset version), `authors`, `spdx`, `retrieved_utc`, `files: [{path, sha256, bytes}]`, `published_outputs: [{name, sha256}]` |
| `src/…` | Upstream files, byte-identical to the recorded hashes |

Rules:

- **No edits under `third_party/`.** Adapters and patches live in
  `src/qcompile/vendored/<component>/`.
- **Modification notice.** Every file there that derives from an upstream
  file starts with a notice: "Derived from <url>@<revision>, <path>. Modified
  by qcompile on <date>: <one-line summary>." (Apache §4(b).)

## 4. Admission checks for a component

A component is admitted only if every check passes. The checks are recorded
in `SOURCE.json` under `admission`.

| Check | Rule |
| --- | --- |
| Explicit licence | A licence file or an author's licence statement at the origin names Apache-2.0. A notebook footer copied by a third party is not enough |
| Generating source | The code that generates the circuit or table is included. A binary `.kmb` or `.npz` alone is not admitted as a member. It may be used only as a hash reference |
| Pinned bytes | Every vendored file has a SHA-256, and published outputs have their hash recorded |
| No competition data | No file from the competition's data, starter kit or metric package is vendored |
| Not denylisted | See below |

Denylist, until a separate change resolves the licence:

- yoyobar's 891-qubit DQI KMB lineage (`993c70386a3d…`), which has no
  explicit source licence;
- the jday96314 Schur continued-fraction decoder, whose repository has no
  licence.

## 5. Regeneration rule

An admitted component becomes an archive member only after our pipeline
rebuilds it from the vendored source in a clean environment. All existing
release gates apply: two identical builds, the pinned metric, and a fresh
confirmation.

### 5.1 Which hash a rebuild is compared with

The comparison hash is the one the **origin** publishes for that output at
the pinned revision. It is read at admission and stored in `SOURCE.json`
under `published_outputs`.

Hash prefixes quoted in any OpenSpec change (for example `fb2da4f2`,
`89357442`, `bce2948f`) are **hints** from a literature survey. They are not
acceptance criteria:

| Situation | Action |
| --- | --- |
| Origin hash matches the hint | Record `hint: match`. |
| Origin hash differs from the hint | Record `hint: mismatch` with both values. Continue with the origin hash. |
| Origin publishes no hash | Record `published_outputs: []`. The rebuild is accepted on verification alone. |

### 5.2 Rebuild outcome

| Output type | Rebuild vs origin hash | Member used |
| --- | --- | --- |
| Circuit (`.kmb`) | Identical | The rebuild |
| Circuit (`.kmb`) | Different | None. The candidate is excluded and the difference recorded |
| Floating-point table (`.npz`) | Identical | The rebuild |
| Floating-point table (`.npz`) | Different | Apply 5.3 |

### 5.3 Floating-point exception (stated once, used by every change)

A fit can differ in the last bits between BLAS builds. For a table whose
rebuild is not bit-identical:

1. Verify both the rebuilt table and the published bytes with the official
   verifier, each with the same loaders.
2. `equivalent`: both pass every constraint and their `λ_eff` agree within
   1×10⁻⁶ relative. The member is the **published bytes**, pinned by hash.
   Both hashes are recorded.
3. `divergent_rebuild`: the rebuilt table passes, but the two are not
   equivalent. The member is the **rebuilt table**.
4. Otherwise the table is not used.

There is no such exception for circuits.

## 6. Policy text

- In `AGENTS.md`, replace "Keep public-source reproduction distinct from an
  independently generated circuit" with:

  > "Vendored public sources are admitted only under `third_party/` with
  > licence, provenance and hashes, and members are regenerated by our
  > pipeline. Keep vendored members and independently generated members
  > distinct in every receipt."

- Add the same rule to `CLAUDE.md`.
- Add a short "Licensing and third-party sources" section to `README.md`
  that points to `LICENSE`, `NOTICE` and `third_party/`.

## 7. Test

Add `tests/test_third_party.py`. It checks that:

- `LICENSE` exists, begins with `Apache License`, contains
  `Version 2.0, January 2004` and `END OF TERMS AND CONDITIONS`, and matches
  the SHA-256 in `licenses.json`;
- every `third_party/*/SOURCE.json` is valid, with each listed file present
  and hash-equal;
- each component has a `LICENSE`, and `NOTICE` names it;
- no file under `third_party/` matches the competition-data filename list in
  `contracts/`.
