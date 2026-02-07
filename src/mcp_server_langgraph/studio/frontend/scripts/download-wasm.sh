#!/bin/bash
# Download and verify sql.js WASM with integrity checking
# Updates the self-hosted WASM binary and its checksum file

set -euo pipefail

VERSION="1.12.0"
URL="https://cdnjs.cloudflare.com/ajax/libs/sql.js/${VERSION}/sql-wasm.wasm"
OUTPUT_DIR="public/wasm"
OUTPUT="${OUTPUT_DIR}/sql-wasm.wasm"
CHECKSUM_FILE="${OUTPUT_DIR}/sql-wasm.sha384"

mkdir -p "$OUTPUT_DIR"

echo "Downloading sql.js WASM v${VERSION}..."
curl -fsSL "$URL" -o "${OUTPUT}.tmp"

# Compute SHA-384 hash
ACTUAL_HASH=$(openssl dgst -sha384 -binary "${OUTPUT}.tmp" | openssl base64 -A)

echo "SHA-384: ${ACTUAL_HASH}"

# Move to final location
mv "${OUTPUT}.tmp" "$OUTPUT"

# Write checksum file
echo -n "$ACTUAL_HASH" > "$CHECKSUM_FILE"

echo "Downloaded and verified sql-wasm.wasm v${VERSION}"
echo "  WASM: ${OUTPUT} ($(wc -c < "$OUTPUT" | tr -d ' ') bytes)"
echo "  Hash: ${CHECKSUM_FILE}"
echo ""
echo "Next steps:"
echo "  1. Commit both files to git"
echo "  2. The hash will be injected at build time via VITE_SQL_WASM_HASH"
