# G1 build report

Authoring host: Windows 11 / Git Bash, repo `wzdm` on branch `main`.
Only the files listed in `docs/G1_README.md` §6 were created; no other worker's
files were touched.

## Artifacts authored

- `.github/workflows/ci.yml` — backend pytest + SBOM job, frontend `npm ci && npm run build` job, synthetic PHI-free env, `contents: read`, no hardcoded secrets.
- `Dockerfile`, `.dockerignore` — venv-based two-stage image, non-root UID/GID 10001, secrets excluded from build context.
- `infrastructure/{main,variables,outputs,versions}.tf`, `infrastructure/environments/dev.tfvars.example` — resource group, private synthetic-artifact storage, Log Analytics, identity/IAM placeholders, commented remote-state TODO.
- `scripts/generate-sbom.sh` — CycloneDX JSON generator with `pip-licenses` fallback.
- `docs/G1_README.md`, `docs/G1_BUILD_REPORT.md` — runbook and this report.

## Executed and verified

| Command | Result |
| --- | --- |
| `bash -n scripts/generate-sbom.sh` | Passed. |
| `bash scripts/generate-sbom.sh` | Passed: `bomFormat=CycloneDX`, `specVersion=1.6`, 60 components, written to `artifacts/sbom-backend.cyclonedx.json` (generated file removed after verification; regenerate on demand). |
| Backend pytest with synthetic env (`SUPABASE_URL=https://synthetic-project.supabase.co`, `DATABASE_URL=postgresql://synthetic:...`, `./venv/Scripts/python.exe -m pytest -q --tb=no`) | Exit 0 — 75 passed, 1 skipped. |
| `npm ci --no-audit --no-fund && npm run build` in `frontend/` | Exit 0 — 179 packages installed, Vite 8.3.8 build succeeded (`dist/` produced). |
| PyYAML `BaseLoader` parse of `.github/workflows/ci.yml` | Valid YAML; jobs `backend`, `frontend` parsed. |
| Static HCL delimiter check on all 5 Terraform files | Zero unbalanced `{}`, `[]`, `()` counts. |

Notes: an earlier pytest run without synthetic env vars produced 3 failures
(401 vs 200); the green run above used the same synthetic values CI sets. A
concurrent worker was editing `backend/app/**`, `backend/tests/**` and
`frontend/src/**` during verification. No Python source files were authored, so
`py_compile` was not applicable; the script's embedded Python heredocs ran
successfully as part of the SBOM run.

## Authored but not executed

- `terraform init/validate/plan` — `terraform` CLI is not installed on this host; only static delimiter checks were possible. Remote state remains a human TODO in `versions.tf`.
- `docker build` — `docker` CLI is not installed on this host.
- `pip-licenses` fallback branch — not exercised (primary `cyclonedx-bom` path succeeded).
- GitHub Actions run, container signing/provenance attestation, separated accounts, signed ADRs, threat-model review — human-owned; no claim is made here.

## Remaining gate gaps

Green synthetic build and SBOM generation are demonstrable locally. Reviewed
infrastructure plan, separated accounts, signed ADRs, threat model, and the
signed artifact path are still human-owned per `docs/G1_README.md` §5; this
delivery does not close G1 on its own.
