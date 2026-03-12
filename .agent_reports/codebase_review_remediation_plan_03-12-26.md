Problem: The review in `.agent_reports/codebase_review_report_03-12-26.md` identifies gaps across testing, security, state management, documentation, performance, and release hygiene. The goal is to remediate all findings in a staged way that reduces risk quickly, establishes guardrails, and avoids destabilizing the working tagging pipeline.

Approach:
- Tackle the work in dependency order: first add safety nets and close critical security holes, then improve correctness and operational reliability, then address maintainability, performance, and documentation debt.
- Group related findings into implementation streams so fixes land coherently across code, tests, and docs.
- Validate each stream with the repository’s existing commands before moving to the next stream.
- Treat “all issues” as a roadmap with phased delivery rather than one unsafe mega-change.

Workstreams:

1. Safety foundations
- Add an automated Python test suite with `pytest` and `pytest-asyncio`.
- Cover metadata merge behavior, scanner behavior, sandbox enforcement, and model recommendation logic.
- Add a minimal CI workflow to run tests and the future lint step on push/PR.

2. Critical security remediation
- Enforce sandbox checks in `/api/tag` for both input and output paths.
- Pin Florence-2 `trust_remote_code=True` model revision.
- Add bounds validation for `threshold` and `max_tags`.
- Add baseline HTTP security headers.
- Harden PID file naming and process validation.
- Make log download use a fixed resolved log directory.

3. Server correctness and state handling
- Replace `is_processing` with a real synchronization primitive.
- Replace queue drain TOCTOU logic with `get_nowait()` handling.
- Bound `log_queue` and `progress_queue`.
- Handle SSE client disconnects cleanly.
- Consider introducing a lightweight job context or persisted job history where the current review calls out structural limitations.

4. Dependency and code quality baseline
- Add Ruff configuration and integrate it into the workflow.
- Normalize dependency version constraints for FastAPI/Uvicorn and relax the Transformers pin if compatible after test coverage exists.
- Improve type coverage in `server.py`.
- Extract magic numbers into named constants.
- Fix minor import-order issues.

5. Florence-2 maintainability hardening
- Document the compatibility patch with upstream references and tested versions.
- Narrow or redesign monkey-patching scope if feasible without regressions.
- Reassess optional dependency split between CLIP-only and Florence-enabled installs.

6. Docs and developer experience
- Add a spec-oriented document describing intended behavior and edge cases.
- Update README CLI docs for `--overwrite` and model aliases.
- Document frontend build steps and API usage.
- Add CONTRIBUTING, CHANGELOG, and LICENSE files.

7. Deployability and operational hygiene
- Add `/health` readiness endpoint and browser-open polling.
- Extend `setup.sh` to handle npm/CSS build when available.
- Add Dependabot config.
- Decide whether compiled CSS remains committed or becomes generated-only.
- Optionally add container or service definitions only after the local workflow is stabilized.

8. Performance improvements
- Cache CLIP tag embeddings.
- Move heavy Florence/PyTorch imports behind lazy initialization.
- Revisit browse pagination and scan streaming if still valuable after core fixes land.

Execution order:
- Phase 1: test harness, security fixes, and regression coverage for those fixes.
- Phase 2: server correctness, queue/state handling, and health/readiness behavior.
- Phase 3: linting, dependency policy, typing, and maintainability refactors.
- Phase 4: documentation, contributor workflow, release metadata, and packaging cleanup.
- Phase 5: performance optimizations and optional architectural improvements.

Todos:
- `remediate-test-foundation`: create test scaffolding, add coverage for critical paths, and document how tests run.
- `remediate-sandbox-and-input-security`: close sandbox bypass, validate request bounds, and lock down log path handling.
- `remediate-remote-code-risk`: pin Florence model revision and document the trust boundary.
- `remediate-server-concurrency`: replace boolean mutex, harden queue handling, and clean up SSE disconnect behavior.
- `remediate-http-hardening`: add security headers and safer PID/process handling.
- `remediate-ci-and-linting`: add CI workflow, Ruff config, and initial lint adoption strategy.
- `remediate-dependencies`: normalize dependency constraints and prepare optional install split.
- `remediate-maintainability`: add constants, type annotations, import cleanup, and patch documentation.
- `remediate-docs-spec`: create spec/developer docs, README fixes, API docs, and release/supporting docs.
- `remediate-dev-setup-and-health`: add `/health`, improve daemon startup checks, and teach `setup.sh` npm/CSS behavior.
- `remediate-performance`: cache embeddings, lazy-load heavy imports, and evaluate pagination/streaming improvements.
- `remediate-repo-hygiene`: add Dependabot, license, changelog, contributing guide, and decide CSS artifact policy.

Notes:
- Some findings overlap; implement them once in the most coherent workstream rather than duplicating fixes.
- The review includes both immediate bugs and long-term improvements. The plan preserves that distinction so high-risk items ship first.
- Certain recommendations (containerization, persisted job history, job context refactor, optional dependency split) should be validated against the desired scope before implementation, but they remain in the roadmap so the review is fully covered.
