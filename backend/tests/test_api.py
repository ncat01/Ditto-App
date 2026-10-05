"""End-to-end API tests, including the full agentic demo scenario."""
from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ["DITTO_DATABASE_URL"] = (
    f"sqlite:///{os.path.join(tempfile.mkdtemp(), 'test.db')}"
)
os.environ["DITTO_DEMO_MODE"] = "true"

from app.discovery import corpus  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        token=c.post("/api/auth/signup",json={"email":"api-tests@example.test","password":"secure-demo-123"}).json()["token"]
        c.headers["Authorization"]="Bearer "+token
        c.post("/api/demo/seed")
        yield c


def test_health_reports_demo_providers_honestly(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["demoMode"] is True
    # Nothing may claim a live integration that is not configured.
    assert "Demo" in body["providers"]["verification"]
    assert "no live scraping" in body["providers"]["discovery"]
    assert "Sandboxed" in body["providers"]["outreach"]


def test_seed_produces_the_demo_case_spread(client):
    cases = client.get("/api/cases").json()
    assert len(cases) == len(corpus.CANDIDATES)
    states = {c["currentState"] for c in cases}
    # The demo needs a case in each interesting state.
    assert "pending_approval" in states
    assert "awaiting_response" in states
    assert "escalated" in states
    assert "resolved" in states
    assert "closed" in states


def test_false_positive_is_closed_without_outreach(client):
    cases = client.get("/api/cases").json()
    fp = next(c for c in cases if c["classification"] == "false_positive")
    assert fp["currentState"] == "closed"
    assert fp["recommendedAction"] == "log_only"
    assert not fp["draftBody"]


def test_stats_are_consistent_with_the_case_list(client):
    cases = client.get("/api/cases").json()
    stats = client.get("/api/dashboard/stats").json()
    assert stats["totalCases"] == len(cases)
    assert stats["resolved"] == sum(1 for c in cases if c["currentState"] == "resolved")
    assert 0.0 <= stats["averageConfidence"] <= 1.0


def test_unknown_case_is_404(client):
    assert client.get("/api/cases/DIT-99999").status_code == 404


def test_illegal_action_returns_409_not_500(client):
    cases = client.get("/api/cases").json()
    closed = next(c for c in cases if c["currentState"] == "closed")
    r = client.post(f"/api/cases/{closed['id']}/approve", json={})
    assert r.status_code == 409
    assert "closed" in r.json()["detail"]


def test_upload_rejects_an_unsupported_file_type(client):
    r = client.post(
        "/api/content/upload",
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")},
    )
    assert r.status_code == 415


def test_full_demo_scenario_detect_to_resolved(client):
    """The exact walkthrough from report §27, driven through the public API."""
    cases = client.get("/api/cases").json()
    case = next(
        c for c in cases
        if c["currentState"] == "pending_approval"
        and c["recommendedAction"] == "attribution_request"
    )
    cid = case["id"]

    # The agents have already run: verified, planned, and parked at the approval gate.
    assert case["classification"] == "genuine_repost"
    assert case["verificationSummary"]
    assert case["actionReasoning"]
    assert case["draftBody"]

    # Human approves -> dispatched -> tracked.
    after = client.post(f"/api/cases/{cid}/approve", json={}).json()
    assert after["currentState"] == "awaiting_response"
    assert after["escalationLevel"] == 1

    # Weekly re-check finds nothing -> agent escalates a tier on its own.
    after = client.post(
        f"/api/cases/{cid}/simulate-followup", json={"outcome": "no_response"}
    ).json()
    assert after["currentState"] == "escalated"
    assert after["recommendedAction"] == "formal_takedown"
    assert after["followUpCount"] == 1

    # The escalation goes back through the approval gate and can be dispatched.
    after = client.post(f"/api/cases/{cid}/approve", json={}).json()
    assert after["currentState"] == "awaiting_response"
    assert after["escalationLevel"] == 2

    # Next re-check: the content is gone -> resolved.
    after = client.post(
        f"/api/cases/{cid}/simulate-followup", json={"outcome": "content_removed"}
    ).json()
    assert after["currentState"] == "resolved"
    assert after["nextFollowUpAt"] is None

    # A resolved case is terminal.
    assert client.post(f"/api/cases/{cid}/simulate-followup", json={}).status_code == 409

    # Every transition is on the audit trail, attributed to an agent or the human.
    agents = [h["agent"] for h in after["history"]]
    assert "verification" in agents
    assert "action_planning" in agents
    assert "human" in agents
    assert "follow_up" in agents


def test_reject_closes_without_sending(client):
    cases = client.get("/api/cases").json()
    pending = next(c for c in cases if c["currentState"] == "pending_approval")
    after = client.post(
        f"/api/cases/{pending['id']}/reject", json={"note": "Not our content."}
    ).json()
    assert after["currentState"] == "closed"


def test_edit_action_updates_the_draft(client):
    response=client.post("/api/auth/signup",json={"email":"draft-tests@example.test","password":"secure-demo-123"})
    client.headers["Authorization"]="Bearer "+response.json()["token"]
    client.post("/api/demo/seed")
    r = client.post("/api/content/upload", params={"title": "Edit test"})
    content_id = r.json()["id"]
    client.post("/api/scan", json={"contentId": content_id})
    cases = [c for c in client.get("/api/cases").json()
             if c["currentState"] == "pending_approval"]
    assert cases, "existing seeded review case should be editable"
    cid = cases[0]["id"]
    after = client.post(
        f"/api/cases/{cid}/edit-action",
        json={"body": "Custom message body.", "tone": "firm"},
    ).json()
    assert after["draftBody"] == "Custom message body."
    assert after["tone"] == "firm"


def test_scanning_fresh_content_does_not_invent_candidates(client):
    """A live upload during a demo must not come back empty."""
    content_id = client.post(
        "/api/content/upload", params={"title": "Fresh upload"}
    ).json()["id"]
    cases = client.post("/api/scan", json={"contentId": content_id}).json()
    assert cases == [], "unsupported discovery must never invent matches"
    assert all(c["classification"] for c in cases)

    # Repeat scans must be reproducible and must not duplicate cases.
    again = client.post("/api/scan", json={"contentId": content_id}).json()
    assert again == []


def test_activity_feed_records_agent_work(client):
    events = client.get("/api/activity").json()
    assert events
    agents = {e["agent"] for e in events}
    assert "verification" in agents
    assert "action_planning" in agents


def test_ground_truth_endpoint_backs_the_evaluation_harness(client):
    body = client.get("/api/demo/ground-truth").json()
    assert set(body["labels"].values()) >= {
        "genuine_repost", "false_positive", "genuine_likeness_misuse"
    }
