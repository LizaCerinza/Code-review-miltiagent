#!/usr/bin/env bash
# Devuelve la imagen Docker que debe ejecutar la Action.
#
#   resolve-image.sh <action_ref> [imagen_forzada] [imagen_base]
#
# vX / vX.Y / vX.Y.Z -> <imagen_base>:X / :X.Y / :X.Y.Z
# main               -> <imagen_base>:edge
# imagen_forzada     -> tiene prioridad sobre todo lo anterior
# Cualquier otra referencia (rama, SHA) falla: no hay una imagen publicada para ella.
set -euo pipefail

ref="${1:-}"
override="${2:-}"
base="${3:-ghcr.io/lizacerinza/code-review-miltiagent}"

if [[ -n "$override" ]]; then
  echo "$override"
  exit 0
fi

if [[ "$ref" =~ ^v([0-9]+(\.[0-9]+){0,2})$ ]]; then
  echo "${base}:${BASH_REMATCH[1]}"
  exit 0
fi

if [[ "$ref" == "main" ]]; then
  echo "${base}:edge"
  exit 0
fi

echo "No hay una imagen publicada para la referencia '${ref}'. Usa un tag de versión" \
  "(@v1, @v1.2.0), @main o la entrada 'image'." >&2
exit 1
