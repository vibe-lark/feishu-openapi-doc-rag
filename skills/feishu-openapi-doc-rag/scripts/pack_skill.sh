#!/bin/sh
set -eu

SKILL_DIR="${1:?usage: pack_skill.sh <skill-dir> [out-dir]}"
OUT_DIR="${2:-$(pwd)}"

NAME="$(basename "$SKILL_DIR")"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="$OUT_DIR/${NAME}-${TS}.tar.gz"

tar -C "$(dirname "$SKILL_DIR")" -czf "$OUT" "$NAME"
echo "$OUT"

