#!/bin/bash
# Provision the offline Vosk Japanese ASR model into MODEL_PATH (babbly/ja/model).
#
# The model is a large, uncommitted asset. This script downloads and unpacks it
# so the offline voice loop can run. Idempotent: it is a no-op if a model is
# already present.
#
# Defaults to the small Japanese model (~50 MB), good for MacBook development.
# For production/Pi accuracy, set VOSK_MODEL=vosk-model-ja-0.22 (~1 GB).
#
#   ./tools/provision_vosk_model.sh
#   VOSK_MODEL=vosk-model-ja-0.22 ./tools/provision_vosk_model.sh
#   MODEL_DIR=/opt/babbly/model ./tools/provision_vosk_model.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="${MODEL_DIR:-$ROOT_DIR/babbly/ja/model}"
MODEL_NAME="${VOSK_MODEL:-vosk-model-small-ja-0.22}"
BASE_URL="${VOSK_BASE_URL:-https://alphacephei.com/vosk/models}"
URL="$BASE_URL/${MODEL_NAME}.zip"

if [[ -f "$MODEL_DIR/conf/model.conf" || -f "$MODEL_DIR/am/final.mdl" ]]; then
  echo "Vosk model already present at $MODEL_DIR — nothing to do."
  exit 0
fi

for tool in curl unzip; do
  command -v "$tool" >/dev/null 2>&1 || { echo "error: '$tool' is required" >&2; exit 2; }
done

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Downloading $URL ..."
curl -fL --retry 3 -o "$tmp/model.zip" "$URL"

echo "Unpacking ..."
unzip -q "$tmp/model.zip" -d "$tmp"

src="$tmp/$MODEL_NAME"
if [[ ! -d "$src" ]]; then
  src="$(find "$tmp" -maxdepth 1 -type d -name 'vosk-model-*' | head -1)"
fi
if [[ -z "${src:-}" || ! -d "$src" ]]; then
  echo "error: could not locate the unpacked model directory" >&2
  exit 3
fi

mkdir -p "$(dirname "$MODEL_DIR")"
rm -rf "$MODEL_DIR"
mv "$src" "$MODEL_DIR"

echo "Vosk model '$MODEL_NAME' provisioned at $MODEL_DIR"
