#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CIRCUIT_DIR="$ROOT_DIR/circuits"
BUILD_DIR="$CIRCUIT_DIR/build"
PTAU_POWER="${POI_PTAU_POWER:-14}"

for command_name in circom node npm openssl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Required command not found: %s\n' "$command_name" >&2
    exit 1
  fi
done
if ! [[ "$PTAU_POWER" =~ ^[0-9]+$ ]] || (( PTAU_POWER < 12 || PTAU_POWER > 28 )); then
  printf 'POI_PTAU_POWER must be an integer between 12 and 28.\n' >&2
  exit 1
fi

cd "$ROOT_DIR"
npm install --no-save --no-package-lock circomlib@2.0.5 snarkjs@0.7.5
SNARKJS="$ROOT_DIR/node_modules/.bin/snarkjs"
mkdir -p "$BUILD_DIR"

circom "$CIRCUIT_DIR/policy_verifier.circom" \
  --r1cs --wasm --sym \
  -l "$ROOT_DIR/node_modules" \
  -o "$BUILD_DIR"

"$SNARKJS" powersoftau new bn128 "$PTAU_POWER" "$BUILD_DIR/pot${PTAU_POWER}_0000.ptau" -v
"$SNARKJS" powersoftau contribute \
  "$BUILD_DIR/pot${PTAU_POWER}_0000.ptau" \
  "$BUILD_DIR/pot${PTAU_POWER}_0001.ptau" \
  --name="PoI local setup" \
  -e="$(openssl rand -hex 32)"
"$SNARKJS" powersoftau prepare phase2 \
  "$BUILD_DIR/pot${PTAU_POWER}_0001.ptau" \
  "$BUILD_DIR/pot${PTAU_POWER}_final.ptau" -v
"$SNARKJS" groth16 setup \
  "$BUILD_DIR/policy_verifier.r1cs" \
  "$BUILD_DIR/pot${PTAU_POWER}_final.ptau" \
  "$BUILD_DIR/policy_verifier_0000.zkey"
"$SNARKJS" zkey contribute \
  "$BUILD_DIR/policy_verifier_0000.zkey" \
  "$BUILD_DIR/policy_verifier_final.zkey" \
  --name="PoI local setup" \
  -e="$(openssl rand -hex 32)"
"$SNARKJS" zkey export verificationkey \
  "$BUILD_DIR/policy_verifier_final.zkey" \
  "$BUILD_DIR/verification_key.json"

printf '\nCircuit artifacts written to %s\n' "$BUILD_DIR"
printf '%s\n' 'This local ceremony is for development only. Use an independently audited, multi-party ceremony for production keys.'