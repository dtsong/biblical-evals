#!/usr/bin/env bash
set -euo pipefail

# Preflight checks for issue #2 migration cutover.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT_DIR/terraform"

required_commands=(gh terraform)

echo "[preflight] Checking required commands"
for cmd in "${required_commands[@]}"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[preflight] Missing command: $cmd"
    exit 1
  fi
done

echo "[preflight] Verifying migration board exists"
test -f "$ROOT_DIR/docs/gcp-migration-board.md"

echo "[preflight] Verifying phase tracking issues exist"
for n in 3 4 5 6 7 8; do
  gh issue view "$n" --json number >/dev/null
done

echo "[preflight] Terraform formatting and validation"
terraform -chdir="$TF_DIR" fmt -check -recursive
terraform -chdir="$TF_DIR" init -backend=false >/dev/null
terraform -chdir="$TF_DIR" validate >/dev/null

echo "[preflight] SUCCESS"
echo "Next: copy terraform/biblical-evals-prod.tfvars.example to local tfvars and begin phase 2 when phase 1 outputs are ready."
