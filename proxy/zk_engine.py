"""Asynchronous Groth16 proof verification through the SnarkJS CLI."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_VKEY = Path(__file__).resolve().parents[1] / "circuits" / "build" / "verification_key.json"
VERIFY_TIMEOUT_SECONDS = float(os.environ.get("POI_VERIFY_TIMEOUT_SECONDS", "15"))
MAX_PROOF_BYTES = 1_000_000


def _json_size(value: Any) -> int:
    return len(json.dumps(value, separators=(",", ":")).encode("utf-8"))


async def verify_proof(
    proof: dict[str, Any],
    public_signals: list[str],
    *,
    verification_key_path: Path | None = None,
) -> bool:
    """Return whether SnarkJS accepts proof for exactly the supplied public signals."""
    if _json_size(proof) > MAX_PROOF_BYTES:
        return False
    if len(public_signals) != 2 or any(not item.isdecimal() for item in public_signals):
        return False

    verification_key = verification_key_path or Path(
        os.environ.get("POI_VERIFICATION_KEY", str(DEFAULT_VKEY))
    )
    if not verification_key.is_file():
        return False

    try:
        with tempfile.TemporaryDirectory(prefix="poi-verify-") as temp_dir:
            temp_path = Path(temp_dir)
            proof_path = temp_path / "proof.json"
            public_path = temp_path / "public.json"
            proof_path.write_text(json.dumps(proof), encoding="utf-8")
            public_path.write_text(json.dumps(public_signals), encoding="utf-8")

            process = await asyncio.create_subprocess_exec(
                os.environ.get("SNARKJS_BIN", "snarkjs"),
                "groth16",
                "verify",
                str(verification_key),
                str(public_path),
                str(proof_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(), timeout=VERIFY_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return False

            return process.returncode == 0 and b"OK" in stdout
    except (OSError, ValueError, TypeError, asyncio.SubprocessError):
        return False