#!/usr/bin/env bash
# Upload bundled demo PDFs (Vision POC). Requires FastAPI on API_URL (default http://localhost:8000).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOC_PROC="$(cd "$SCRIPT_DIR/.." && pwd)"
DEMO="$DOC_PROC/samples/demo"
API_URL="${API_URL:-http://localhost:8000}"

if [[ ! -f "$DEMO/Eng-Arabic.pdf" || ! -f "$DEMO/809508119-Iqama.pdf" ]]; then
  echo "Missing demo PDFs under $DEMO" >&2
  exit 1
fi

echo "POST $API_URL/upload?audit_target=vision_poc&user_id=1"
curl -sS -X POST "${API_URL}/upload?audit_target=vision_poc&user_id=1" \
  -F "files=@${DEMO}/Eng-Arabic.pdf" \
  -F "files=@${DEMO}/809508119-Iqama.pdf"
echo ""
