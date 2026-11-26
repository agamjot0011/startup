# G1 — Step 7 build, CI and infrastructure guide

Scope: handbook Step 7 (W1–W3, gate G1) — protected monorepo, CI/CD, signed
artifact path, Terraform environments, IAM/logging/encryption baseline,
synthetic data and PHI-free observability. Exit evidence is a **green synthetic
build, SBOM/provenance, reviewed infrastructure plan and separated accounts**
(`HANDBOOK_EXTRACTED.txt`, lines 1107–1112).

This directory set only automates what can be automated. Items under
"Human-owned evidence" are deliberately *not* claimed by these files.

## 1. Continuous integration

Workflow: `.github/workflows/ci.yml`. It triggers on push/PR to `main` and on
manual dispatch, with `permissions: contents: read`.

| Job | What it runs |
| --- | --- |
| `backend` | Selects `backend/venv/bin/python` or `backend/venv/Scripts/python.exe` when present, otherwise `python`; installs `backend/requirements.txt`, runs `python -m pytest -q` from `backend/`, then generates a CycloneDX SBOM via `scripts/generate-sbom.sh` and uploads `artifacts/`. |
| `frontend` | `npm ci` followed by `npm run build` in `frontend/`; uploads `frontend/dist/`. |

The workflow sets **synthetic, PHI-free** values for `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL` and
`FRONTEND_URL`. These point at `.invalid`/loopback hosts and are not secrets.
No real credentials are read or stored by the workflow.

Run the same checks locally (Git Bash shown; POSIX uses `python3` and
`venv/bin/python`):

```bash
export SUPABASE_URL="https://synthetic-project.supabase.co"
export SUPABASE_ANON_KEY="synthetic-anon-key-not-a-secret"
export SUPABASE_SERVICE_ROLE_KEY="synthetic-service-role-key-not-a-secret"
export DATABASE_URL="postgresql://synthetic:synthetic@127.0.0.1:5432/synthetic"

cd backend
./venv/Scripts/python.exe -m pip install -r requirements.txt   # first run only
./venv/Scripts/python.exe -m pytest -q

cd ../frontend
npm ci
npm run build
```

`backend/.env` is gitignored and must never be committed; CI does not use it.

## 2. Backend container image

`Dockerfile` is a two-stage, venv-based image. Build **from the repository root**
so the `backend/` paths resolve, and pass configuration at runtime:

```bash
docker build -f Dockerfile -t wzdm-backend:g1 .
docker run --rm -p 4000:4000 --env-file /path/to/non-committed.env wzdm-backend:g1
```

Properties: Python 3.12 slim runtime, isolated `/opt/venv` copied from the
builder, fixed non-root UID/GID `10001`, no secrets or `.env` files in any layer
(`.dockerignore` excludes them), and an OCI source label pointing at the public
repo. The image is a build skeleton — it does not itself sign or attest anything.

## 3. SBOM / provenance input

```bash
bash scripts/generate-sbom.sh
# -> artifacts/sbom-backend.cyclonedx.json
```

The script creates an isolated venv in `$TMPDIR/wzdm-sbom-venv`, installs
`cyclonedx-bom` and emits a reproducible CycloneDX JSON for
`backend/requirements.txt`. If that install fails it falls back to
`pip-licenses` and converts its JSON into a minimal CycloneDX document. It
validates `bomFormat` before exiting. Override with `PYTHON`, `REQ_FILE`,
`ARTIFACT_DIR`, `SBOM_OUT`, `SBOM_VENV` if needed. CI uploads the artifact in
the `backend` job.

## 4. Terraform environments

Files: `main.tf` (resource group, private synthetic-artifact storage,
PHI-free Log Analytics workspace, user-assigned identity and a conditional
least-privilege role assignment), `variables.tf`, `outputs.tf`, `versions.tf`,
and `environments/dev.tfvars.example`. No credentials, subscription IDs or
state files are committed.

```bash
cd infrastructure
cp environments/dev.tfvars.example environments/dev.tfvars   # local only; edit name
terraform init
terraform validate
terraform plan -var-file=environments/dev.tfvars -out=tfplan
terraform show -json tfplan > ../artifacts/tfplan.json       # evidence for review
```

`dev.tfvars` is a local working file; keep it out of version control. Replace
the placeholder storage account name with a globally unique one per
environment. Authentication uses `ARM_SUBSCRIPTION_ID` plus an OIDC-federated
principal supplied by the hosting environment — never source literals.

`versions.tf` contains a commented `backend "azurerm"` block with an explicit
**TODO(HUMAN)**: enable remote state (versioning, soft-delete, encryption,
restricted access, AAD auth) before applying to any shared environment.

## 5. Human-owned evidence (NOT produced here)

| Gate evidence | Owner / where it lives |
| --- | --- |
| Signed ADRs | Human sign-off in `docs/decision_register.md`; this repo has no signing automation. |
| Reviewed threat model | Security reviewer; must explicitly cover PHI-free logging and tenant boundaries. |
| Separated accounts + reviewed infrastructure plan | Platform/DevOps: separate management/workload/state accounts, OIDC federation, human review of the plan JSON. |
| Signed artifact path / provenance attestation | Release owner: cosign/SLSA-style signing and attestation of the image + SBOM. CI only produces the unsigned inputs. |
| PHI-free observability sign-off | Human review of log schemas and redaction; the Terraform skeleton only creates an empty workspace. |

Nothing in these artifacts asserts that the above items are complete. See
`G1_BUILD_REPORT.md` for exactly what was executed versus authored.

## 6. Repository boundaries

Owned here: `.github/workflows/ci.yml`, `Dockerfile`, `.dockerignore`,
`infrastructure/*`, `scripts/generate-sbom.sh`, `docs/G1_README.md`,
`docs/G1_BUILD_REPORT.md`. Not modified: `backend/app/**`, `frontend/src/**`,
root `README.md`, `.gitignore`.
