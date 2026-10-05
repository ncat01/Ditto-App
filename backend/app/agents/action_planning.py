"""Confidence-calibrated escalation policy — the project's headline contribution.

Weighted, case-specific scoring rather than a fixed strike count. Weights are named
constants so the policy can be tuned and evaluated against a human-reviewer baseline
(report §3, §9).
"""
from __future__ import annotations

from app.agents.base import ActionPlan
from app.models.enums import ActionType, Classification, MessageTone, Severity

W_CONFIDENCE = 0.35
W_SEVERITY = 0.25
W_MONETIZATION = 0.20
W_REACH = 0.10
W_HISTORY = 0.10

T_ATTRIBUTION = 0.45
T_TAKEDOWN = 0.75

# A confirmed match above this confidence always warrants at least an attribution
# request. The escalation policy decides how hard to push, not whether the creator
# gets credit at all: without this floor a high-confidence repost on a small,
# non-monetized account scores below T_ATTRIBUTION and is silently logged.
CONFIRMED_MATCH_CONFIDENCE = 0.75


def _pct(v: float) -> str:
    return f"{int(v * 100)}%"


def _followers(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


def _reach_score(followers: int) -> float:
    if followers >= 500_000:
        return 1.0
    if followers >= 100_000:
        return 0.80
    if followers >= 25_000:
        return 0.55
    if followers >= 5_000:
        return 0.30
    return 0.10


class MockActionPlanningAgent:
    display_name = "Demo Action-Planning Agent (policy-scored)"

    def plan(
        self, content, candidate, verification, prior_escalation_level: int = 0,
        tone: MessageTone = MessageTone.PROFESSIONAL,
    ) -> ActionPlan:
        if getattr(candidate,"attribution_present",False) or getattr(candidate,"permission_granted",False):
            return ActionPlan(action=ActionType.LOG_ONLY,priority=Severity.LOW,reasoning="Credited or explicitly authorized demo reuse; similarity alone does not warrant enforcement.",factors=["Attribution and permission checked separately"],draft_subject="",draft_body="",tone=tone,engine=self.display_name)
        if verification.classification is Classification.FALSE_POSITIVE:
            return ActionPlan(
                action=ActionType.LOG_ONLY,
                priority=Severity.LOW,
                reasoning=(
                    "Verification classified this candidate as a false positive at "
                    f"{_pct(verification.confidence)} confidence. No outbound action is "
                    "warranted; the case is logged so it is not re-surfaced."
                ),
                factors=[
                    "Classification: False positive",
                    f"Confidence: {_pct(verification.confidence)}",
                    "No outbound action permitted for false positives",
                ],
                draft_subject="",
                draft_body="",
                tone=tone,
                engine=self.display_name,
            )

        if verification.classification is Classification.GENUINE_LIKENESS_MISUSE or verification.confidence < .75:
            return ActionPlan(action=ActionType.REVIEW_REQUEST,priority=verification.severity,
                reasoning="Simulated evidence or low rule confidence requires human review. Similarity, attribution and permission are separate.",
                factors=["Human review required","No validated manipulation detector"],
                draft_subject="Review synthetic evidence",draft_body="SANDBOX REVIEW REQUEST: Assess attribution, permission and manipulation separately. No infringement determination or takedown is being made.",tone=tone,engine=self.display_name)
        confidence_score = max(0.0, min(1.0, (verification.confidence - 0.50) / 0.48))
        severity_score = {"low": 0.20, "medium": 0.60, "high": 1.00}[
            verification.severity.value
        ]
        monetization_score = 1.0 if candidate.monetized else 0.15
        reach = _reach_score(candidate.follower_count)
        history = max(0.0, min(1.0, prior_escalation_level / 2.0))

        score = (
            confidence_score * W_CONFIDENCE
            + severity_score * W_SEVERITY
            + monetization_score * W_MONETIZATION
            + reach * W_REACH
            + history * W_HISTORY
        )

        if score >= T_TAKEDOWN:
            action = ActionType.FORMAL_TAKEDOWN
        elif score >= T_ATTRIBUTION:
            action = ActionType.ATTRIBUTION_REQUEST
        elif verification.confidence >= CONFIRMED_MATCH_CONFIDENCE:
            action = ActionType.ATTRIBUTION_REQUEST
        else:
            action = ActionType.LOG_ONLY

        # Escalation ratchet: never propose a weaker tier than already attempted.
        if action.tier < prior_escalation_level:
            action = next(
                a for a in ActionType if a.tier == min(prior_escalation_level, 2)
            )

        factors = [
            f"Confidence {_pct(verification.confidence)} (weight {_pct(W_CONFIDENCE)})",
            f"Severity {verification.severity.value.title()} (weight {_pct(W_SEVERITY)})",
            (
                ("Monetized account" if candidate.monetized else "Non-monetized account")
                + f" (weight {_pct(W_MONETIZATION)})"
            ),
            f"Reach {_followers(candidate.follower_count)} followers "
            f"(weight {_pct(W_REACH)})",
            (
                "First detected incident (no prior action)"
                if prior_escalation_level == 0
                else f"Policy escalation tier {prior_escalation_level} proposed; see actual dispatch history"
            ),
            f"Aggregate escalation score {score:.2f} -> {action.label}"
            + (
                " (raised to the confirmed-match floor)"
                if score < T_ATTRIBUTION and action is ActionType.ATTRIBUTION_REQUEST
                else ""
            ),
        ]

        subject, body = self._draft(action, content, candidate, verification, tone)

        return ActionPlan(
            action=action,
            priority=verification.severity,
            reasoning=self._reasoning(
                action, verification, candidate, prior_escalation_level, score
            ),
            factors=factors,
            draft_subject=subject,
            draft_body=body,
            tone=tone,
            engine=self.display_name,
        )

    @staticmethod
    def _reasoning(action, v, c, prior, score) -> str:
        if action is ActionType.FORMAL_TAKEDOWN and score < T_TAKEDOWN:
            return f"No response triggered a proposed higher tier. Rule score {score:.2f} is below the initial {T_TAKEDOWN} threshold. Fresh approval and review of permission are required."
        if action is ActionType.LOG_ONLY:
            return (
                "Signals are consistent with reuse but fall below the action threshold "
                f"(score {score:.2f} vs {T_ATTRIBUTION} required). The case is logged and "
                "monitored rather than actioned."
            )
        if action is ActionType.ATTRIBUTION_REQUEST:
            money = (
                "on a monetized account. " if c.monetized
                else "with no monetization signals. "
            )
            first = (
                "This is the first detected incident for this account, " if prior == 0
                else "Prior contact has been attempted, "
            )
            floor_note = (
                "Reach and monetization are low, but the match is confirmed, so the "
                "creator is still owed credit. "
                if score < T_ATTRIBUTION else ""
            )
            return (
                f"{_pct(v.confidence)}-confidence "
                f"{v.classification.value.replace('_', ' ')} {money}{first}"
                f"{floor_note}"
                "so a proportionate attribution request is the appropriate first step."
            )
        extras = ""
        if c.monetized:
            extras += ", monetized reuse"
        if c.follower_count >= 100_000:
            extras += f", significant reach ({_followers(c.follower_count)})"
        if prior > 0:
            extras += ", and no resolution from the earlier attribution request"
        return (
            f"Escalation score {score:.2f} exceeds the formal-notice threshold of "
            f"{T_TAKEDOWN}. Drivers: {_pct(v.confidence)} confidence, "
            f"{v.severity.value} severity{extras}. A formal takedown notice is warranted."
        )

    @staticmethod
    def _draft(action, content, c, v, tone) -> tuple[str, str]:
        if action is ActionType.LOG_ONLY:
            return "", ""

        published = content.published_at.strftime("%d %B %Y")

        if action is ActionType.ATTRIBUTION_REQUEST:
            subject = f'Attribution request for "{content.title}"'
            if tone is MessageTone.FIRM:
                body = (
                    f"Hi {c.account_handle},\n\n"
                    f"Your post on {c.platform} reuses original content titled "
                    f'"{content.title}" (published {published}) without attribution.\n\n'
                    "Please add clear credit to the original creator, or remove the post, "
                    "within 7 days.\n\nSent via Ditto on behalf of the creator"
                )
            elif tone is MessageTone.NEUTRAL:
                body = (
                    f"Hi {c.account_handle},\n\n"
                    f"This is a notice regarding your post on {c.platform}, which our "
                    f'review matched against original content titled "{content.title}", '
                    f"published {published}.\n\nWe are requesting attribution to the "
                    "original creator.\n\nSent via Ditto on behalf of the creator"
                )
            else:
                body = (
                    f"Hi {c.account_handle},\n\n"
                    f"We noticed that your recent post on {c.platform} appears to reuse "
                    f'original content titled "{content.title}", first published on '
                    f"{published}.\n\nWe're glad the work resonated — we'd simply like it "
                    "credited. Could you please add clear attribution to the original "
                    "creator in the caption?\n\nThanks for your time,\n"
                    "Sent via Ditto on behalf of the creator"
                )
            return subject, body

        subject = f'Formal notice of unauthorized use — "{content.title}"'
        body = (
            "FORMAL NOTICE OF UNAUTHORIZED USE\n\n"
            f"Platform: {c.platform}\n"
            f"Reported account: {c.account_handle}\n"
            f"Reported URL: {c.source_url}\n"
            f'Original work: "{content.title}"\n'
            f"First published: {published}\n\n"
            "We are the rights holder of the original work identified above. The reported "
            "post reuses that work without permission or attribution.\n\n"
            "Evidence of match:\n"
            f"  - Verification confidence: {_pct(v.confidence)}\n"
            f"  - Assessed severity: {v.severity.value}\n"
            f"  - Observed modifications: {c.transform_note}\n\n"
            "Review the timeline for prior contact; this draft does not establish that contact occurred.\n\n"
            "We request removal of the infringing material, or the addition of clear "
            "attribution, under the platform's copyright policy.\n\n"
            "We have a good-faith belief that the use described is not authorized by the "
            "rights holder, its agent, or the law.\n\n"
            "Submitted via Ditto on behalf of the creator"
        )
        return subject, body
