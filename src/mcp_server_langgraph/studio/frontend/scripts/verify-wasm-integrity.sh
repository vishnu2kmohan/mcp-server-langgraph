#!/bin/bash
# Verify sql.js WASM integrity before bundling
# Run during CI/CD to prevent supply chain attacks

set -euo pipefail

WASM_FILE="public/wasm/sql-wasm.wasm"
EXPECTED_VERSION="1.12.0"
CHECKSUM_FILE="public/wasm/sql-wasm.sha384"

# Verify file exists
if [[ ! -f "$WASM_FILE" ]]; then
  echo "ERROR: WASM file not found at $WASM_FILE"
  echo "Run: npm run download-wasm to fetch the verified version"
  exit 1
fi

# Verify checksum file exists
if [[ ! -f "$CHECKSUM_FILE" ]]; then
  echo "ERROR: Checksum file not found at $CHECKSUM_FILE"
  echo "Run: npm run download-wasm to generate the checksum"
  exit 1
fi

# Compute SHA-384 hash (SRI format: base64 of binary hash)
ACTUAL_HASH=$(openssl dgst -sha384 -binary "$WASM_FILE" | openssl base64 -A)
EXPECTED_HASH=$(cat "$CHECKSUM_FILE")

if [[ "$ACTUAL_HASH" != "$EXPECTED_HASH" ]]; then
  echo "ERROR: WASM integrity check failed!"
  echo "Expected: $EXPECTED_HASH"
  echo "Actual:   $ACTUAL_HASH"
  echo ""
  echo "This could indicate:"
  echo "  1. The WASM file was tampered with"
  echo "  2. The version was updated without updating the checksum"
  echo ""
  echo "To fix: re-run 'npm run download-wasm' to download a verified copy"
  exit 1
fi

echo "WASM integrity verified: sql-wasm.wasm (v${EXPECTED_VERSION})"
