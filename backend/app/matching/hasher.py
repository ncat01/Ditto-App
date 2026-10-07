"""Measured perceptual hashes; missing or unreadable files fail explicitly."""
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
    raise ValueError("A real media file is required; fingerprint unavailable")




def similarity(a: str, b: str) -> float:
    """Normalized Hamming similarity between two 64-bit hex hashes."""
    try:
        return 1.0 - (bin(int(a, 16) ^ int(b, 16)).count("1") / 64.0)
    except (ValueError, TypeError):
        return 0.0
