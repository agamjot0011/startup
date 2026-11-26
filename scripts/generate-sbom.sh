#!/usr/bin/env bash
# Generate a CycloneDX JSON SBOM for the backend requirements into artifacts/.
# Usage: bash scripts/generate-sbom.sh   (all paths are resolved from this script)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ_FILE="${REQ_FILE:-$ROOT_DIR/backend/requirements.txt}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$ROOT_DIR/artifacts}"
OUT_FILE="${SBOM_OUT:-$ARTIFACT_DIR/sbom-backend.cyclonedx.json}"
VENV_DIR="${SBOM_VENV:-${TMPDIR:-/tmp}/wzdm-sbom-venv}"

# Git Bash passes POSIX paths verbatim to native Windows executables; convert
# them so python and the CLI read the intended files. No-op on POSIX systems.
to_native_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}
NATIVE_VENV_DIR="$(to_native_path "$VENV_DIR")"
NATIVE_REQ_FILE="$(to_native_path "$REQ_FILE")"
NATIVE_OUT_FILE="$(to_native_path "$OUT_FILE")"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "ERROR: requirements file not found: $REQ_FILE" >&2
  exit 1
fi
mkdir -p "$ARTIFACT_DIR"

# Pick an interpreter (python3 on POSIX, python on Windows/Git Bash).
if [[ -n "${PYTHON:-}" ]]; then
  BASE_PY="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  BASE_PY="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  BASE_PY="$(command -v python)"
else
  echo "ERROR: no python interpreter found" >&2
  exit 1
fi

# Work in an isolated venv so the caller's environment is never mutated.
detect_venv_python() {
  local candidate
  for candidate in "$VENV_DIR/bin/python" "$VENV_DIR/Scripts/python.exe"; do
    if [[ -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if ! SBOM_PY="$(detect_venv_python)"; then
  "$BASE_PY" -m venv "$NATIVE_VENV_DIR"
  SBOM_PY="$(detect_venv_python)"
fi
"$SBOM_PY" -m pip install --disable-pip-version-check --quiet --upgrade pip >/dev/null

generated="none"
if "$SBOM_PY" -m pip install --disable-pip-version-check --quiet cyclonedx-bom >/dev/null 2>&1; then
  CLI_CMD=()
  for candidate in \
    "$VENV_DIR/bin/cyclonedx-py" "$VENV_DIR/Scripts/cyclonedx-py.exe" \
    "$VENV_DIR/bin/cyclonedx-bom" "$VENV_DIR/Scripts/cyclonedx-bom.exe"; do
    if [[ -x "$candidate" ]]; then CLI_CMD=("$candidate"); break; fi
  done
  if (( ${#CLI_CMD[@]} == 0 )); then CLI_CMD=("$SBOM_PY" -m cyclonedx_bom); fi

  if [[ "${CLI_CMD[*]}" == *"cyclonedx-py"* || "${CLI_CMD[*]}" == *" -m cyclonedx_bom"* ]]; then
    if "${CLI_CMD[@]}" requirements "$NATIVE_REQ_FILE" --of JSON -o "$NATIVE_OUT_FILE" \
        --output-reproducible --sv 1.6 >/dev/null 2>&1 && [[ -s "$OUT_FILE" ]]; then
      generated="cyclonedx-bom (cyclonedx-py requirements)"
    fi
  elif "${CLI_CMD[@]}" -i "$NATIVE_REQ_FILE" -o "$NATIVE_OUT_FILE" -F json >/dev/null 2>&1 \
      && [[ -s "$OUT_FILE" ]]; then
    generated="cyclonedx-bom (legacy CLI)"
  fi
fi

if [[ "$generated" == "none" ]]; then
  echo "cyclonedx-bom unavailable; falling back to pip-licenses" >&2
  "$SBOM_PY" -m pip install --disable-pip-version-check --quiet pip-licenses >/dev/null
  RAW="$ARTIFACT_DIR/pip-licenses.json"
  NATIVE_RAW="$(to_native_path "$RAW")"
  "$SBOM_PY" -m piplicenses --format=json --with-urls >"$RAW"
  "$SBOM_PY" - "$NATIVE_RAW" "$NATIVE_OUT_FILE" <<'PY'
import json
import sys

raw_path, out_path = sys.argv[1], sys.argv[2]
with open(raw_path, encoding="utf-8") as fh:
    rows = json.load(fh)

components = []
for row in rows:
    component = {
        "type": "library",
        "name": row.get("Name", ""),
        "version": row.get("Version", ""),
    }
    license_name = (row.get("License") or "").strip()
    if license_name and license_name.lower() not in {"unknown", "none", "n/a"}:
        component["licenses"] = [{"license": {"name": license_name}}]
    url = (row.get("URL") or "").strip()
    if url:
        component["externalReferences"] = [{"type": "website", "url": url}]
    components.append(component)

bom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {
        "component": {"type": "application", "name": "wzdm-backend", "version": "0.1.0"},
        "tools": [{"vendor": "wzdm", "name": "scripts/generate-sbom.sh", "version": "1.0"}],
    },
    "components": components,
}
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(bom, fh, indent=2)
PY
  generated="pip-licenses-fallback"
fi

# Basic structural check before declaring success.
"$SBOM_PY" - "$NATIVE_OUT_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    bom = json.load(fh)
if bom.get("bomFormat") != "CycloneDX":
    raise SystemExit("invalid SBOM: bomFormat is not CycloneDX")
print(f"SBOM components: {len(bom.get('components', []))}")
PY

echo "Wrote CycloneDX SBOM via $generated -> $OUT_FILE"
