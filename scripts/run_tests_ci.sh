#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
ARTIFACTS_DIR="$ROOT_DIR/ci_artifacts"

print_step() {
  echo "➜ $1"
}

print_success() {
  echo "✓ $1"
}

print_step "Preparing virtual environment"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
  print_success "Created venv at $VENV_DIR"
else
  print_success "Using existing venv at $VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

print_step "Installing dependencies"
python -m pip install uv
uv pip install -r "$ROOT_DIR/requirements.txt"

print_step "Cleaning previous artifacts"
rm -rf "$ARTIFACTS_DIR" report.xml coverage.xml
mkdir -p "$ARTIFACTS_DIR"

print_step "Running pytest with coverage"
pytest "$ROOT_DIR/tests" \
  --junitxml="$ROOT_DIR/report.xml"

print_step "Collecting artifacts"
cp "$ROOT_DIR/report.xml" "$ARTIFACTS_DIR/"
cp "$ROOT_DIR/coverage.xml" "$ARTIFACTS_DIR/"

print_success "CI-like test run completed"
print_success "Artifacts stored in $ARTIFACTS_DIR"