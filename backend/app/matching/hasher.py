"""Perceptual hashing. Uses the ImageHash/Pillow pHash implementation named in the
report; falls back to a deterministic seed-derived hash when the file cannot be
decoded (unsupported codec, or seeded demo content with no backing file)."""
from __future__ import annotations

import io

DISPLAY_NAME = "pHash 64-bit (ImageHash/Pillow)"


def fingerprint(data: bytes | None, seed: int = 1) -> str:
    if data:
        try:
            import imagehash
            from PIL import Image

            image = Image.open(io.BytesIO(data))
            return str(imagehash.phash(image))
        except Exception as exc:
            raise ValueError("Unsupported or unreadable media; fingerprint unavailable") from exc
    return synthetic_hash(seed)


def synthetic_hash(seed: int) -> str:
    x = (seed * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 30
    x = (x * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 27
    x = (x * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 31
    return f"{x:016x}"


def similarity(a: str, b: str) -> float:
    """Normalized Hamming similarity between two 64-bit hex hashes."""
    try:
        return 1.0 - (bin(int(a, 16) ^ int(b, 16)).count("1") / 64.0)
    except (ValueError, TypeError):
        return 0.0
