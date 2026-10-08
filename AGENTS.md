# AGENTS.md — gufo_acme

`gufo_acme` is a Python asyncio client for the ACME protocol (RFC 8555, a.k.a.
Let's Encrypt), part of the Gufo Stack. It ships `AcmeClient` (base) and
fulfillment clients (`dav`, `powerdns`, `web`) under the namespace package
`gufo.acme`. Pure Python, fully typed, security-focused.

## Dev environment

- Python >= 3.11; CI matrix tests 3.11–3.14.
- Run development commands through `scripts/run-dev`, which executes them in
  the running devcontainer. For example: `scripts/run-dev ruff --version`.
- Install development tooling in the container with
  `scripts/run-dev pip install -e '.[test,lint,docs,ipython]'` when needed.
- **All tests, linters, formatters, and project scripts must run through
  `scripts/run-dev`. Direct execution on the host is not allowed.** This also
  applies to package and documentation build commands. If the devcontainer is
  not running, start it before running these commands; do not fall back to the
  host environment.
- The devcontainer (`.devcontainer/devcontainer.json`, target `dev`) sets
  `PYTHONPATH=src` and provides ruff format-on-save. To format explicitly, run
  `scripts/run-dev ruff format examples/ src/ tests/`.

## Build & test

Run the following commands from the project root through `scripts/run-dev`.
The container has `PYTHONPATH=src`, as configured in
`.devcontainer/devcontainer.json`:

```
scripts/run-dev ruff format --check examples/ src/ tests/   # format gate
scripts/run-dev ruff check -q examples/ src/ tests/         # lint gate
scripts/run-dev mypy src/                                   # types (strict, see pyproject)
scripts/run-dev python -m pytest -v tests/                  # test suite
scripts/run-dev python -m pytest -v --cov --cov-branch --cov-report=xml tests/
```

Build docs: `scripts/run-dev mkdocs serve` (local) /
`scripts/run-dev mkdocs gh-deploy --strict --force` (CI).
Build package: `scripts/run-dev python -m build --sdist --wheel` → `dist/`.

## Conventions (observed)

- **File banner** at top of most modules: a `# ---...---` separator,
  `# Gufo ACME: <module title>`, `# Copyright (C) <years>, Gufo Labs`, separator.
- **Import grouping** with comment headers: `# Python modules`, `# Third-party
  modules`, `# Gufo ACME modules`. isort orders by group; first-party = `src`.
- **Ruff**: `line-length = 79` (short!), `target-version = py311`, style enforced
  for `E/W/F/C90/I/D/YTT/ANN/S/BLE/B/A/C4/EM/ISC/ICN/PT/RET/SIM/PL/PIE/RUF/UP`.
  Google docstring convention; double docstring quotes; `f401` unfixable.
- **mypy strict** (set in pyproject): full type annotations, no `Any`
  (`ANN401` ignored only for return-type hints).
- snake_case modules/classes/exceptions. No self/cls annotations in signatures.
- **Async tests** use `asyncio.run()` wrappers — there is no pytest-asyncio or
  `asyncio_mode` config; do not add `@pytest.mark.asyncio`.
- **CHANGELOG.md**: Keep a Changelog format; bump `__version__` in
  `src/gufo/acme/__init__.py` (also read by setuptools dynamic version).
- **Commits**: short, imperative subjects (e.g. `ruff: Enforce UP checks`,
  `Fix link`); feature branches are kebab-case (e.g. `ruff-up`, `faq`).

## Pitfalls

- **Meta-tests act as gates — editing may break them:**
  - `tests/test_ci.py` enforces exact pinned GitHub Action versions
    (cache@v5, checkout@v6, setup-python@v6, …). Bump the workflow version and
    update the `VERSIONS` list in lockstep.
  - `tests/test_docs.py` rejects `datatracker.ietf.org` links (must use
    `rfc-editor.org/rfc/<n>.html`) and flags unused/duplicated link defs in
    `docs/**/*.md`.
  - `tests/test_project.py` requires a fixed `REQUIRED_FILES` list that **must stay
    sorted**; keep it in sync when adding/removing top-level files.
- **Network tests skip by default** (`@pytest.mark.skipif(not_set(...))`).
  They need env vars: `CI_ACME_TEST_DOMAIN`/`_USER`/`_PASS`,
  `CI_DAV_TEST_DOMAIN`/`_USER`/`_PASSWORD`,
  `CI_POWERDNS_TEST_DOMAIN`/`_API_URL`/`_API_KEY`, and `CI_GOOGLE_EAB_KID`/`_HMAC`.
  Missing vars → skipped, not failed (expected locally).
- **Generated — do not hand-edit:** `dist/` (build/coverage output),
  `docs/reference/*` + `SUMMARY.md` (produced by `docs/gen_doc_stubs.py` via
  `mkdocs-gen-files`), `dist/coverage/index.html`. `.gitignore` already excludes
  `dist/`/`build/`/`*.egg-info`.
- `tests/clients/test_web.py` and some test files omit the full banner (just the
  `#  Python modules` group comment) — match the file's existing style; don't
  retrofit a banner it lacks.
