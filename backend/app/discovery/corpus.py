"""Synthetic, fully-labelled discovery corpus (report §8).

Ground truth is recorded alongside each candidate so precision/recall can be
measured. Positive examples use the transformations the report proposes: crop,
watermark, re-encode, aspect-ratio change and caption overlay.

Live scraping of Instagram is out of scope; it breaches their Terms of Service.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

DISPLAY_NAME = "Demo discovery corpus (synthetic, no live scraping)"

CREATOR_NAME = "Alex Morgan"
CREATOR_HANDLE = "@alexmorgan.shoots"


def _days_ago(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


@dataclass
class SeedContent:
    id: str
    title: str
    kind: str
    perceptual_hash: str
    palette_seed: int
    published_days_ago: int


@dataclass
class SeedCandidate:
    id: str
    content_id: str
    platform: str
    account_name: str
    account_handle: str
    source_url: str
    caption: str
    follower_count: int
    monetized: bool
    hash_similarity: float
    visual_similarity: float
    caption_similarity: float
    face_similarity: float
    posted_days_ago: int
    transform_note: str
    palette_seed: int
    ground_truth: str
    attribution_present: bool = False
    permission_granted: bool = False


CONTENT: list[SeedContent] = [
    SeedContent("content_001", "Sunset Travel Reel", "video", "c3f1a04d8b2e7615", 1, 62),
    SeedContent("content_002", "Studio Portrait Series", "video", "9a72e5c1f0d43b88", 2, 48),
    SeedContent("content_003", "Coastal Drone Pass", "video", "5e0bd7431ca9f262", 3, 35),
    SeedContent("content_004", "Morning Market Walk", "video", "71c4a9e2350fb8d6", 4, 21),
    SeedContent("content_005", "Rooftop Golden Hour", "video", "e2d80b67a145c3f9", 5, 12),
]

CANDIDATES: list[SeedCandidate] = [
    SeedCandidate(
        "cand_001", "content_001", "Instagram", "Travel Reuploads", "@travel_reuploads",
        "https://instagram.com/reel/demo-Cx7Kq2ZtA",
        "Golden hour hits different 🌅 #travel #sunset #reels",
        84_300, False, 0.94, 0.96, 0.87, 0.0, 9,
        "Cropped to 4:5 with a watermark overlay in the lower-right corner.",
        1, "genuine_repost",
    ),
    SeedCandidate(
        "cand_002", "content_003", "Instagram", "Aerial Daily", "@aerial.daily",
        "https://instagram.com/reel/demo-Dp4Mn8Yq1",
        "Drone shot of the week ✈️ Link in bio for our presets!",
        612_000, True, 0.97, 0.98, 0.62, 0.0, 28,
        "Re-encoded at a lower bitrate with a burned-in caption bar at the top.",
        3, "genuine_repost",
    ),
    SeedCandidate(
        "cand_003", "content_002", "Pinterest", "Portrait Lighting Ideas",
        "@portraitlighting", "https://pinterest.com/pin/demo-8841203",
        "Soft key light setup — studio inspiration board",
        12_400, False, 0.48, 0.55, 0.31, 0.12, 94,
        "Similar studio lighting setup and framing, different subject.",
        2, "false_positive",
    ),
    SeedCandidate(
        "cand_004", "content_004", "Instagram", "City Food Diary", "@cityfooddiary",
        "https://instagram.com/reel/demo-Bt2Lm9Wr6",
        "Saturday market runs 🥬 (repost)",
        9_800, False, 0.95, 0.93, 0.71, 0.0, 16,
        "Aspect ratio changed to 1:1 with the original audio retained.",
        4, "genuine_repost",
    ),
    SeedCandidate(
        "cand_005", "content_005", "Ad Library (synthetic)", "GlowUp Skincare Co",
        "@glowup.skincare", "https://example-adlibrary.demo/ad/8813--synthetic",
        "Real results, real people. Try GlowUp today.",
        41_000, True, 0.31, 0.44, 0.08, 0.91, 6,
        "No frame-level match to any published original, but facial geometry matches "
        "the creator closely — consistent with a generated likeness.",
        5, "genuine_likeness_misuse",
    ),
    SeedCandidate(
        "cand_006", "content_001", "Instagram", "Wanderlust Clips", "@wanderlust.clips",
        "https://instagram.com/reel/demo-Az9Pq3Vk4",
        "Sunsets like these 🔥 follow for daily travel content",
        158_000, True, 0.92, 0.94, 0.55, 0.0, 41,
        "Zoom-cropped with a text overlay covering the original corner mark.",
        1, "genuine_repost",
    ),
]


def content_published_at(item: SeedContent) -> datetime:
    return _days_ago(item.published_days_ago)


def candidate_posted_at(item: SeedCandidate) -> datetime:
    return _days_ago(item.posted_days_ago)


def candidates_for(content_id: str) -> list[SeedCandidate]:
    return [c for c in CANDIDATES if c.content_id == content_id]


# ---------------------------------------------------------------- synthesis


_SYNTH_ACCOUNTS = [
    ("Repost Central", "@repost.central"),
    ("Daily Clip Vault", "@dailyclipvault"),
    ("Viral Reels Hub", "@viralreelshub"),
    ("Trend Archive", "@trend.archive"),
    ("Clip Curator", "@clip.curator"),
]

_SYNTH_CAPTIONS = [
    "Found this and had to share 🔥 #reels #viral",
    "This is everything ✨ credit to the creator",
    "Saving this one for later 📌",
    "POV: the perfect shot #contentcreator",
]

_SYNTH_TRANSFORMS = [
    "Cropped to 4:5 with a watermark overlay.",
    "Re-encoded at a lower bitrate with a caption bar burned in.",
    "Aspect ratio changed to 1:1, original audio retained.",
    "Zoom-cropped and re-uploaded with a text overlay.",
]

_SYNTH_PLATFORMS = ["Instagram", "Instagram", "TikTok", "Facebook"]
_SYNTH_FOLLOWERS = [3_200, 28_500, 91_000, 240_000]


def synthesise_for(content) -> list[SeedCandidate]:
    """Derive candidates deterministically from an uploaded item's own fingerprint.

    Freshly uploaded content has no entry in the seeded corpus, so a live scan during
    a demo would otherwise return nothing. Deriving from the hash keeps repeat scans
    of the same upload reproducible.
    """
    seed = int(content.perceptual_hash[:8], 16)
    count = 2 + (seed % 2)  # 2-3 candidates
    out: list[SeedCandidate] = []

    for i in range(count):
        strong = i == 0
        name, handle = _SYNTH_ACCOUNTS[(seed + i * 31) % len(_SYNTH_ACCOUNTS)]
        spread = ((seed >> (i * 3)) % 100) / 100.0
        h = round(0.88 + spread * 0.09, 2) if strong else round(0.38 + spread * 0.30, 2)
        v = round(min(0.98, max(0.25, h + (spread - 0.4) * 0.08)), 2)
        cap = round(0.60 + spread * 0.30, 2) if strong else round(0.10 + spread * 0.35, 2)

        out.append(
            SeedCandidate(
                id=f"cand_live_{content.id[-8:]}_{i}",
                content_id=content.id,
                platform=_SYNTH_PLATFORMS[(seed + i * 7) % len(_SYNTH_PLATFORMS)],
                account_name=name,
                account_handle=handle,
                source_url=f"https://demo-corpus.local/post/{(seed + i) % 999999}",
                caption=_SYNTH_CAPTIONS[(seed + i * 13) % len(_SYNTH_CAPTIONS)],
                follower_count=_SYNTH_FOLLOWERS[(seed + i * 5) % len(_SYNTH_FOLLOWERS)],
                monetized=strong and (seed % 2 == 0),
                hash_similarity=h,
                visual_similarity=v,
                caption_similarity=cap,
                face_similarity=0.0,
                # Candidates always post after the original in the demo corpus.
                posted_days_ago=-(3 + i * 4),
                transform_note=_SYNTH_TRANSFORMS[(seed + i * 3) % len(_SYNTH_TRANSFORMS)],
                palette_seed=content.palette_seed,
                ground_truth="genuine_repost" if strong else "false_positive",
            )
        )
    return out

from dataclasses import replace
CANDIDATES.extend([
    replace(CANDIDATES[0],id="cand_007",account_handle="@credited.demo",attribution_present=True,ground_truth="genuine_repost"),
    replace(CANDIDATES[0],id="cand_008",account_handle="@authorized.demo",permission_granted=True,ground_truth="genuine_repost"),
    replace(CANDIDATES[0],id="cand_009",account_handle="@ambiguous.demo",caption_similarity=0.0,ground_truth="genuine_repost"),
])
