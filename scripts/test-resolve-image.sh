#!/usr/bin/env bash
# Pruebas de resolve-image.sh. Uso: bash scripts/test-resolve-image.sh
set -uo pipefail

script="$(dirname "$0")/resolve-image.sh"
base="ghcr.io/lizacerinza/code-review-miltiagent"
failures=0

expect() {
  local expected="$1"; shift
  local actual
  actual="$(bash "$script" "$@" 2>/dev/null)"
  if [[ "$actual" != "$expected" ]]; then
    echo "FALLA: resolve-image.sh $* -> '$actual' (esperado '$expected')"
    failures=$((failures + 1))
  fi
}

expect_error() {
  if bash "$script" "$@" >/dev/null 2>&1; then
    echo "FALLA: resolve-image.sh $* debió fallar"
    failures=$((failures + 1))
  fi
}

expect "$base:1" v1
expect "$base:1.2" v1.2
expect "$base:1.2.3" v1.2.3
expect "$base:edge" main
expect "otra/imagen:dev" v1 "otra/imagen:dev"
expect "otra/imagen:dev" feature/x "otra/imagen:dev"
expect "ghcr.io/fork/repo:0" v0 "" "ghcr.io/fork/repo"
expect_error feature/x
expect_error 3f2a9c1
expect_error v1.2.3.4
expect_error ""

if [[ $failures -gt 0 ]]; then
  echo "$failures prueba(s) fallaron"
  exit 1
fi
echo "resolve-image.sh: todas las pruebas pasaron"
