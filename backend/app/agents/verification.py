"""Demo Verification Agent — the server-side twin of the Kotlin implementation.

Deterministic weighted rules over the same signal set a vision-capable LLM would
receive. Always labelled as a demo engine so no live-AI claim is implied.
"""
from __future__ import annotations

from datetime import timezone

from app.agents.base import Signal, VerificationResult
from app.models.enums import Classification, Severity


def _pct(v: float) -> str:
    return f"{int(v * 100)}%"


def _followers(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


class MockVerificationAgent:
    display_name = "Demo Verification Agent (deterministic)"

    def verify(self, content, candidate) -> VerificationResult:
        h = candidate.hash_similarity
        v = candidate.visual_similarity
        cap = candidate.caption_similarity

        posted = candidate.posted_at
        published = content.published_at
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)

        posted_after = posted > published
        days_after = max(0, (posted - published).days)

        score = (h * 0.45) + (v * 0.35) + (cap * 0.10)
        score += 0.10 if posted_after else -0.15

        likeness = candidate.id.split(":")[-1] == "cand_005"  # Explicit simulated scenario, never a face-only inference.

        if likeness:
            classification = Classification.GENUINE_LIKENESS_MISUSE
        elif score >= 0.72 and posted_after:
            classification = Classification.GENUINE_REPOST
        else:
            classification = Classification.FALSE_POSITIVE

        boundary = 0.80 if likeness else 0.72
        margin = abs(score - boundary)
        if classification is Classification.FALSE_POSITIVE:
            confidence = min(0.94, 0.55 + margin * 1.4)
        elif classification is Classification.GENUINE_LIKENESS_MISUSE:
            confidence = min(0.97, 0.60 + candidate.face_similarity * 0.35)
        else:
            confidence = min(0.98, 0.62 + margin * 1.8)
        confidence = round(max(0.50, min(0.98, confidence)), 2)

        severity = self._severity(classification, candidate, score)

        signals = [
            Signal("Hash similarity", _pct(h), h >= 0.70),
            Signal("Visual similarity", _pct(v), v >= 0.70),
            Signal("Caption context", _pct(cap), cap >= 0.60),
            Signal(
                "Publication order",
                f"Posted {days_after}d after original" if posted_after
                else "Posted before original",
                posted_after,
            ),
            Signal(
                "Account context",
                f"{_followers(candidate.follower_count)} followers",
                candidate.follower_count > 5_000,
            ),
            Signal(
                "Monetization",
                "Monetized account" if candidate.monetized else "No monetization signals",
                candidate.monetized,
            ),
        ]
        if candidate.face_similarity > 0:
            signals.append(
                Signal(
                    "Simulated face signal (detector unavailable)",
                    _pct(candidate.face_similarity),
                    candidate.face_similarity >= 0.80,
                )
            )

        return VerificationResult(
            classification=classification,
            confidence=confidence,
            severity=severity,
            summary=self._summary(classification, candidate, posted_after, days_after),
            signals=signals,
            evidence_summary=(
                f"Compared the original fingerprint ({content.perceptual_hash[:12]}…) "
                f"against the candidate on {candidate.platform}. "
                f"{candidate.transform_note}"
            ),
            engine=self.display_name,
        )

    @staticmethod
    def _severity(classification, candidate, score) -> Severity:
        if classification is Classification.FALSE_POSITIVE:
            return Severity.LOW
        if classification is Classification.GENUINE_LIKENESS_MISUSE:
            return Severity.HIGH
        if candidate.monetized and candidate.follower_count >= 50_000:
            return Severity.HIGH
        if candidate.monetized or candidate.follower_count >= 50_000:
            return Severity.MEDIUM
        return Severity.MEDIUM if score >= 0.90 else Severity.LOW

    @staticmethod
    def _summary(classification, candidate, posted_after, days_after) -> str:
        if classification is Classification.GENUINE_REPOST:
            note = candidate.transform_note[:1].lower() + candidate.transform_note[1:]
            tail = (
                f"It was published {days_after} days after the original, and the caption "
                "carries no attribution back to the creator. "
                if posted_after else ""
            )
            return (
                f"The detected post closely matches the original despite {note} {tail}"
                "High visual and hash agreement makes genuine reuse the most likely "
                "explanation."
            )
        if classification is Classification.GENUINE_LIKENESS_MISUSE:
            return (
                "SIMULATED altered-speech / fake-endorsement scenario. No real face, "
                "transcript or manipulation detector was run. A matching face does not "
                "prove manipulation or absent permission. Human review required."
            )

        reason = (
            "the candidate predates the original content, " if not posted_after
            else "hash and caption agreement are both weak, "
        )
        return (
            "Surface-level similarity is present, but the supporting signals do not hold "
            f"up: {reason}which is more consistent with coincidental resemblance than reuse."
        )
