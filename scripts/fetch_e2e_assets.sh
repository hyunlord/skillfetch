#!/usr/bin/env bash
# Download the e2e release asset, verify it against evals/e2e/ASSETS.tsv, and unpack its files
# in place under evals/e2e/ (label and result files over 1 MB, judge-package diffs).
#   scripts/fetch_e2e_assets.sh            # from GitHub releases (curl)
#   scripts/fetch_e2e_assets.sh FILE.tar.gz  # from a local copy
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
E2E="$ROOT/evals/e2e"
LIST="$E2E/ASSETS.tsv"
REPO="hyunlord/skillfetch"

header="$(head -1 "$LIST")"   # "# release <tag>, asset <name>, <bytes> bytes, sha256 <hex>"
TAG="$(sed -E 's/^# release ([^,]+),.*/\1/' <<<"$header")"
NAME="$(sed -E 's/.* asset ([^,]+),.*/\1/' <<<"$header")"
WANT="$(sed -E 's/.* sha256 ([0-9a-f]{64}).*/\1/' <<<"$header")"

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
if [[ $# -ge 1 ]]; then
  cp "$1" "$tmp/$NAME"
else
  curl -fsSL -o "$tmp/$NAME" "https://github.com/$REPO/releases/download/$TAG/$NAME"
fi

got="$(sha256 "$tmp/$NAME")"
if [[ "$got" != "$WANT" ]]; then
  echo "fetch_e2e_assets: $NAME sha256 $got, expected $WANT" >&2
  exit 1
fi

mkdir -p "$tmp/x"
tar -xzf "$tmp/$NAME" -C "$tmp/x"
n=0
while IFS=$'\t' read -r path _bytes digest _rest; do
  [[ "$path" == path || "$path" == \#* || -z "$path" ]] && continue
  if [[ "$(sha256 "$tmp/x/$path")" != "$digest" ]]; then
    echo "fetch_e2e_assets: $path does not match ASSETS.tsv" >&2
    exit 1
  fi
  mkdir -p "$E2E/$(dirname "$path")"
  cp "$tmp/x/$path" "$E2E/$path"
  n=$((n + 1))
done < "$LIST"
echo "fetch_e2e_assets: $n files verified and unpacked under evals/e2e/ ($TAG)"
