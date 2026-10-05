# Ditto

**An Agentic AI Content Credit System**

> Stay on it until it's resolved.

Ditto finds where a creator's content has been reused without credit, verifies whether
the match is genuine, decides what response it warrants, asks a human to approve, and
then keeps the case open — re-checking, escalating or resolving it — until it is done.

The differentiator is not detection. It is the loop:

```
DETECT → VERIFY → DECIDE → HUMAN APPROVAL → ACT → WAIT → RE-CHECK → ESCALATE / RESOLVE
```

---

## Table of contents

1. [What's in the box](#whats-in-the-box)
2. [Architecture](#architecture)
3. [Agent architecture](#agent-architecture)
4. [Case state machine](#case-state-machine)
5. [The escalation policy (project novelty)](#the-escalation-policy-project-novelty)
6. [Android app](#android-app)
7. [Backend](#backend)
8. [Database](#database)
9. [Demo Mode](#demo-mode)
10. [Running the 3–5 minute demo](#running-the-35-minute-demo)
11. [Building the APK](#building-the-apk)
12. [Testing](#testing)
13. [API configuration](#api-configuration)
14. [Security](#security)
15. [Implemented vs. mocked vs. future](#implemented-vs-mocked-vs-future)
16. [Known limitations](#known-limitations)
17. [Roadmap](#roadmap)

---

## What's in the box

```
Ditto Phoneapp/
├── android/                  Native Android client (Kotlin + Jetpack Compose)
│   └── app/src/main/java/com/ditto/app/
│       ├── domain/           Models, agents, state machine  ← the brain
│       ├── data/             Room persistence, demo corpus, pHash, repositories
│       ├── ui/               Theme, components, screens
│       ├── viewmodel/        StateFlow-backed ViewModels
│       └── navigation/       Nav graph + bottom bar
├── backend/                  FastAPI service (mirror implementation)
│   └── app/
│       ├── agents/           Verification, action-planning, follow-up
│       ├── api/              Routes + Pydantic schemas
│       ├── database/         SQLAlchemy engine/session
│       ├── discovery/        Synthetic labelled corpus
│       ├── matching/         pHash
│       ├── models/           Enums + ORM tables
│       └── services/         Case orchestration, state machine, seeding
├── demo_data/                Ground-truth labels for the evaluation harness
├── docker-compose.yml
└── README.md
```

---

## Architecture

Ditto is the six cooperating layers described in the project report. Detection
(layers 1–3) and the agentic decision loop (layers 4–6) are decoupled so each can be
tested independently.

| # | Layer | What it does | Where |
|---|-------|--------------|-------|
| 1 | **Ingestion** | Takes the creator's own content, generates a perceptual fingerprint | `data/demo/PerceptualHasher.kt`, `app/matching/hasher.py` |
| 2 | **Discovery** | Surfaces candidate reuse from a synthetic corpus | `data/demo/MockDiscoveryProvider.kt`, `app/discovery/corpus.py` |
| 3 | **Verification Agent** | Classifies each candidate with a confidence, severity and written rationale | `domain/agents/MockVerificationAgent.kt`, `app/agents/verification.py` |
| 4 | **Action-Planning Agent** | Scores the case and chooses log / attribution / takedown | `domain/agents/MockActionPlanningAgent.kt`, `app/agents/action_planning.py` |
| 5 | **Human Approval Gate** | Shows evidence, reasoning and draft; nothing is sent without approval | `ui/screens/CaseSheets.kt`, `POST /api/cases/{id}/approve` |
| 6 | **Follow-Up Agent** | Re-evaluates open cases on a schedule; escalates or resolves | `domain/agents/MockFollowUpAgent.kt`, `app/agents/follow_up.py` |

### Why the agent logic lives on the device *and* on the server

The report specifies FastAPI, and the backend implements the full pipeline. But the
demo requirement is that **the whole loop works offline**, so a Wi-Fi failure during a
viva cannot take the presentation down.

So the domain layer — the three agents plus the state machine — is implemented in
Kotlin and runs against Room on the device, behind a `DittoRepository` interface. The
same logic ships in Python for the FastAPI deployment. The UI depends only on the
interface, so swapping a Retrofit-backed repository in for the local one changes no
screen code.

Both implementations are covered by equivalent test suites, which is what keeps them
honest about staying in step.

---

## Agent architecture

The agents are **decision-making components, not chatbots**. Each has a defined input,
a decision, a rationale, and where applicable a requested state transition.

### Verification Agent

```
INPUT   CandidateMatch + the creator's original ContentItem
REASONS hash similarity · visual similarity · caption context
        publication order · account reach · monetization · face-embedding distance
OUTPUT  classification ∈ {genuine_repost, genuine_likeness_misuse, false_positive}
        confidence, severity, decision summary, per-signal breakdown
```

Confidence is derived from **distance to the decision boundary**, not the raw score —
a case that only just clears the threshold reports low confidence, which is what makes
the downstream escalation policy meaningful.

The likeness-misuse path keys on an inverted signature: high facial similarity with
*low* hash similarity means the face matches but no published frame does, which is
characteristic of generated content rather than a re-upload.

### Action-Planning Agent

```
INPUT   verified case + prior escalation level
OUTPUT  action ∈ {log_only, attribution_request, formal_takedown}
        priority, reasoning, weighted policy factors, drafted message
```

### Follow-Up Agent

```
INPUT   case + history + observed outcome of the weekly re-check
OUTPUT  next action (wait / nudge / escalate / resolve), target tier, reasoning
        + a requested state transition, which the state machine validates
```

An escalation **raises the action tier and returns the case to the approval gate**. The
agent proposes; the human still decides. It never dispatches on its own.

---

## Case state machine

The lifecycle from the report, enforced in the domain layer:

```
new ──▶ verified ──▶ pending_approval ──▶ sent ──▶ awaiting_response
                                                        │
                                          ┌─────────────┼─────────────┐
                                          ▼             ▼             ▼
                                      escalated     resolved       closed
                                          │
                                          └──▶ sent (re-dispatch at a higher tier)
```

**The UI cannot set a state.** It requests an action; the domain layer decides whether
the implied transition is legal. Illegal transitions are refused — the API returns
`409 Conflict`, and the app shows an explanatory error rather than silently doing
nothing.

| From | To | Allowed |
|------|----|---------|
| `new` | `verified`, `closed` | ✅ |
| `verified` | `pending_approval`, `closed` | ✅ |
| `pending_approval` | `sent`, `closed` | ✅ |
| `sent` | `awaiting_response`, `resolved`, `closed` | ✅ |
| `awaiting_response` | `escalated`, `resolved`, `closed` | ✅ |
| `escalated` | `sent`, `awaiting_response`, `resolved`, `closed` | ✅ |
| `resolved` / `closed` | — | ❌ terminal |
| `new` | `resolved` | ❌ |
| `verified` | `sent` | ❌ (cannot skip the approval gate) |

---

## The escalation policy (project novelty)

The report's headline contribution is a **confidence-calibrated escalation policy**:
case-adaptive judgement rather than a fixed "3 strikes" rule.

Each case is scored on weighted, case-specific signals:

| Signal | Weight |
|--------|--------|
| Verification confidence | 35% |
| Severity | 25% |
| Monetization indicators | 20% |
| Account reach | 10% |
| Prior escalation history | 10% |

The aggregate score maps onto an action tier:

```
score ≥ 0.75  →  Formal Takedown Notice
score ≥ 0.45  →  Attribution Request
otherwise     →  Log Only
```

Two guards sit on top of the raw score:

- **Confirmed-match floor.** A match verified above 0.75 confidence always warrants at
  least an attribution request. Without this, a high-confidence repost on a small,
  non-monetized account scores just under the threshold and gets silently logged — the
  creator would never get credit. The policy decides *how hard to push*, not whether
  the creator is owed credit at all.
- **Escalation ratchet.** A follow-up round never proposes a weaker action than the
  tier already attempted on that case.

A false positive **never** produces outbound action, whatever the other signals say.

The weights and thresholds are named constants (`W_CONFIDENCE`, `T_TAKEDOWN`, …) so the
policy can be tuned and evaluated against a human-reviewer baseline, which is the
evaluation method in the report. `GET /api/demo/ground-truth` serves the labelled set
for that harness.

---

## Android app

**Stack:** Kotlin 2.0.21 · Jetpack Compose (BOM 2024.12.01) · Material 3 ·
Navigation Compose · Room 2.6.1 (KSP) · DataStore · Retrofit + OkHttp + kotlinx.serialization ·
Coroutines/StateFlow · Coil · Gradle Kotlin DSL · minSdk 26 · targetSdk 35

**Architecture:** MVVM over a clean domain layer. `ui → viewmodel → repository →
{agents, state machine, Room}`. Dependency wiring is a hand-written `ServiceLocator` —
chosen over Hilt deliberately, since the graph is small and an annotation-processor-free
container keeps the build simple and reliable for a capstone deliverable.

### Screens

| Screen | Purpose |
|--------|---------|
| **Home** | Greeting, live counters, agent activity timeline, cases needing attention |
| **Cases** | Filter by state, search by account/ID/platform, sort by updated/confidence/severity |
| **Scan** | Pick from device or library, staged scan pipeline, match results |
| **Case detail** | Evidence comparison, similarity breakdown, agent reasoning, approval gate, follow-up, lifecycle timeline, full audit history |
| **Activity** | Every autonomous decision, attributed and timestamped |
| **Follow-up** | The queue of cases awaiting a response |
| **Analytics** | Detection and resolution metrics, case distribution |
| **Settings** | Profile, Demo Mode, Presentation Mode, agent preferences, connected platforms, about |
| **AI Likeness Protection** | Honest P2 status page |

### Design system

A warm-paper foundation with deep editorial blues and deliberately muted status colours.

```
Background   #F7F3EA    Primary Blue    #163B5C    Text        #111827
Background₂  #FAF8F3    Secondary Blue  #2E6F95    Text₂       #5F6875
Surface      #FFFFFF    Light Blue      #DCEAF2    Border      #D9D7D0
Surface₂     #F1EEE7    Deep Blue       #0F2D46
```

Typography pairs a serif display voice with a neutral sans for body and data. Corner
radii are restrained (4–14dp), cards are flat with hairline borders, and status hues are
desaturated so they never dominate the page. All of it is centralised in
`ui/theme/`.

### Synthetic evidence rendering

The seeded corpus ships no photographs. Each item is drawn procedurally on a Compose
`Canvas` from its palette seed — a horizon, a subject disc, a foreground mass — so the
same seed always renders the same scene. The "detected" copy is then drawn with its
actual transformation applied: visible zoom-crop, watermark, or a burned-in caption bar.

This means the evidence comparison genuinely *shows* why perceptual hashing is needed,
rather than asserting it in a caption. Real uploads render via Coil instead.

### Perceptual hashing is real

`PerceptualHasher` is a genuine DCT-based 64-bit pHash: decode → 32×32 greyscale →
separable 2-D DCT-II → low-frequency 8×8 block → median threshold. Videos are hashed by
extracting a representative frame via `MediaMetadataRetriever`. If media cannot be
decoded it falls back to a stable seed-derived hash so the demo never breaks.

---

## Backend

**Stack:** Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Uvicorn · Pillow + ImageHash

### Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional; all providers default to Demo Mode
uvicorn app.main:app --reload --port 8010
```

Open http://127.0.0.1:8010/docs for interactive API docs.

> **Port note:** 8010 is used rather than the FastAPI-conventional 8000, which is often
> already taken. Any port works — pass `--port` and update the client's base URL.

The database is created and the demo corpus seeded automatically on first startup.

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Status + **which providers are real vs. demo** |
| `POST` | `/api/content/upload` | Ingest content, generate fingerprint |
| `GET` | `/api/content` | List monitored content |
| `POST` | `/api/scan` | Run discovery → verification → planning |
| `GET` | `/api/cases` | List cases (optional `?state=`) |
| `GET` | `/api/cases/{id}` | Case with full audit history |
| `POST` | `/api/cases/{id}/approve` | Human approval gate |
| `POST` | `/api/cases/{id}/reject` | Reject; closes without sending |
| `POST` | `/api/cases/{id}/edit-action` | Edit draft body and tone |
| `POST` | `/api/cases/{id}/simulate-followup` | Run the Follow-Up Agent |
| `POST` | `/api/cases/{id}/resolve` | Mark resolved |
| `GET` | `/api/dashboard/stats` | Dashboard counters |
| `GET` | `/api/activity` | Agent activity feed |
| `POST` | `/api/demo/seed` | Seed / re-seed (`?force=true`) |
| `GET` | `/api/demo/ground-truth` | Labelled set for the evaluation harness |

**Error handling:** `404` unknown case · `409` illegal state transition ·
`413` file too large · `415` unsupported media type · `422` validation ·
`500` returns a generic message, never a stack trace.

---

## Database

Free and self-hosted — no Supabase, no managed service.

- **On device:** Room / SQLite (`ditto.db`)
- **Backend:** SQLAlchemy over SQLite by default

The ORM uses no SQLite-specific types, so PostgreSQL needs only a URL change:

```bash
DITTO_DATABASE_URL=postgresql+psycopg://ditto:password@localhost:5432/ditto
```

### Entities

`User` · `Content` · `CandidateMatch` · `Case` · `CaseHistory` · `ActivityEvent` ·
`ActionDraft` · `FollowUpEvent`

`Case` carries the candidate, verification result, action plan and lifecycle fields
(`current_state`, `escalation_level`, `follow_up_count`, `next_followup_at`,
`last_action_at`). `CaseHistory` records every transition with timestamp, previous
state, new state, responsible agent, action and reasoning — the explainable audit trail.

---

## Demo Mode

Demo Mode is **on by default** and is what makes the presentation reliable.

- Discovery uses the synthetic labelled corpus — Instagram is never scraped
- Verification uses the deterministic on-device engine — identical results every run
- Outreach is sandboxed — messages are prepared and logged, never transmitted
- Follow-up can be triggered on demand instead of waiting a real week
- Everything works with no network and no API keys

**Presentation Mode** additionally pins agent decisions to be deterministic and shortens
scan stage timings for a clean live walkthrough.

### Honesty about what is real

The app never claims an integration it does not have. Settings shows each provider's
true status, and the UI language reflects it:

| Reality | What Ditto says |
|---------|-----------------|
| No Instagram API | "Demo discovery corpus (synthetic, no live scraping)" |
| No LLM key | "Demo Verification Agent (on-device, deterministic)" |
| Sandboxed SMTP | "Message prepared and recorded. Nothing was transmitted." |
| Likeness pipeline incomplete | "Coming in P2" |

---

## Running the 3–5 minute demo

The app seeds itself on first launch, so there is no setup. Six cases open in a spread
of lifecycle states.

| # | Step | What to point at |
|---|------|------------------|
| 1 | Open Ditto | Counters, agent activity, cases needing attention |
| 2 | **Scan** tab → pick content → **Scan for matches** | Staged pipeline: ingest → fingerprint → discover → verify → prepare |
| 3 | Open the result case | Original vs. detected side by side, with the crop/watermark visible |
| 4 | Read **Verification Agent** | Classification, confidence, signals considered |
| 5 | Read **Action-Planning Agent** | Weighted factors and the aggregate escalation score |
| 6 | Tap **Approve action** | The approval gate — recipient, action, full draft, Demo Mode notice |
| 7 | Approve & send | State moves `pending_approval → sent → awaiting_response` |
| 8 | **Simulate weekly follow-up** → *No response* | Agent escalates: `awaiting_response → escalated`, tier raised to formal notice |
| 9 | Read the decision banner | The agent's reasoning for escalating |
| 10 | Approve the escalation, follow up again → *Content removed* | `→ resolved` |
| 11 | Expand **Case history** | Full audit trail, every step attributed |
| 12 | Back to **Home** | Counters have updated live |

**The line to close on:** no single model call can hold a case open for weeks, decide
when to escalate based on what happened last time, and revise its approach. That loop
is the whole point — and it just ran live.

To reset between runs: **Settings → Reset demo data**.

---

## Building the APK

Requires JDK 17 or 21 (**not** 24 — AGP 8.7 does not support it) and the Android SDK.

```bash
cd android
export JAVA_HOME=/path/to/jdk-21          # e.g. Temurin 21
export ANDROID_HOME=$HOME/Library/Android/sdk

./gradlew assembleDebug        # → app/build/outputs/apk/debug/app-debug.apk
./gradlew assembleRelease      # → app/build/outputs/apk/release/app-release.apk
```

Install on a device or emulator:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

To point the app at a backend:

```bash
./gradlew assembleDebug -PdittoApiBaseUrl=http://10.0.2.2:8010/
```

`10.0.2.2` is how an Android emulator reaches the host machine's `localhost`.

> The release APK is signed with the debug keystore so a runnable release build can be
> produced for the capstone demo. **Generate a real keystore before any production
> release.**

---

## Testing

```bash
# Android — 38 tests
cd android && ./gradlew testDebugUnitTest

# Backend — 57 tests
cd backend && ./.venv/bin/python -m pytest tests/ -q
```

Coverage includes:

- **State machine** — the happy path, the multi-cycle escalation loop, terminal states,
  no backwards movement, and that the approval gate cannot be skipped
- **Verification** — every seeded candidate against its recorded ground truth,
  determinism across runs, the likeness signature, severity mapping
- **Action planning** — false positives never act, the confirmed-match floor, the
  escalation ratchet, tone selection, policy-factor exposure
- **Follow-up** — each outcome's decision, the escalation ceiling, and that the agent
  can never force an illegal state
- **API** — the full demo scenario end to end, `409` on illegal transitions, upload
  rejection, fresh-content scanning, stats consistency, and that `/api/health` never
  claims an unconfigured provider

---

## API configuration

All credentials live in the **backend's** environment. The Android client never holds
provider keys. Copy `backend/.env.example` to `backend/.env`:

```bash
DITTO_DATABASE_URL=sqlite:///./ditto.db
DITTO_DEMO_MODE=true

META_ACCESS_TOKEN=
GOOGLE_CLOUD_API_KEY=
META_AD_LIBRARY_TOKEN=
LLM_API_KEY=

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
```

Every one is optional. A missing key is not an error — that capability falls back to its
Demo Mode implementation and `/api/health` reports the fallback honestly.

---

## Security

- No secrets in source. The backend URL is a build-time property; provider keys are
  server-side environment only, never shipped to the client.
- Uploads are validated on media type (`415`) and size, capped at 25 MB (`413`).
- All user-supplied text is sanitised (control characters stripped, length capped).
- Cleartext HTTP is blocked except for explicit local development hosts
  (`10.0.2.2`, `localhost`, `127.0.0.1`) via `network_security_config.xml`.
- The global exception handler returns a generic message; stack traces are logged
  server-side only.
- The backend is authentication-ready: routes are organised so an auth dependency can be
  applied without restructuring. **Auth is not implemented** — see limitations.
- The human approval gate is not bypassable: no code path dispatches an action without
  an explicit approval call.

---

## Implemented vs. mocked vs. future

### ✅ Fully implemented

- Case state machine with enforced transitions, on both client and server
- All three agents, with reasoning and explainable audit trails
- Human approval gate — approve, edit draft with tone selection, reject
- Follow-up loop with escalation tiers, ceiling, and resolution
- Confidence-calibrated escalation policy with the confirmed-match floor
- Real DCT-based perceptual hashing, on device and on the server
- Room + SQLAlchemy persistence with full case history
- Complete Android UI: 9 screens, live-updating counters, empty and error states
- FastAPI backend with 16 endpoints and proper status codes
- 95 tests across both codebases
- Offline operation with no network and no API keys

### 🟡 Demo / mocked (by design)

- **Discovery** — synthetic labelled corpus. Live Instagram scraping breaches their ToS
  and is deliberately out of scope; the corpus also gives cleaner ground truth for
  evaluation than uncontrolled scraped data.
- **Verification reasoning** — deterministic weighted rules over the same signals a
  vision-capable LLM would receive, so demo runs are reproducible. Labelled as a demo
  engine everywhere it appears.
- **Outreach** — messages are drafted and recorded, never transmitted.
- **Evidence imagery** — procedurally rendered for seeded corpus items.
- **Weekly scheduler** — the cadence is modelled (`next_followup_at`, cron-ready
  `cases_due_for_follow_up()`), but is triggered manually for the demo.

### 🔵 Future (P2)

- InsightFace / ArcFace embedding extraction
- Google Cloud Vision reverse image search
- Meta Graph API and Meta Ad Library integration
- LLM-backed verification with vision input
- Cross-platform identity linking; adversarial-evasion detection
- Deployed Celery beat / cron scheduler
- Authentication and multi-tenancy

---

## Known limitations

1. **Discovery is synthetic.** Ditto does not search the live internet. Real reverse
   image search is a P2 integration; the interfaces for it already exist.
2. **Verification is rule-based, not an LLM.** It is deterministic and explainable, and
   agrees with ground truth on the labelled corpus — but it has not been validated
   against uncontrolled real-world data.
3. **Video fingerprinting samples a single frame.** Adequate for near-duplicate reposts;
   true temporal fingerprinting is future work.
4. **Likeness misuse is architected, not delivered.** The signal, classification path
   and severity mapping exist and a seeded case demonstrates them, but there is no real
   face-embedding pipeline. The app says so.
5. **No authentication.** The backend assumes a single trusted user. Do not expose it
   publicly as-is.
6. **The release APK uses the debug keystore.** Replace before any real distribution.
7. **Commercial-ad coverage is gated.** The Meta Ad Library free tier covers only
   political and social-issue ads; commercial-ad access is researcher-gated, so the
   synthetic ad corpus is the practical substitute.
8. **The two implementations are kept in step by tests, not by generated code.** A
   change to policy logic must be made in both `domain/agents/` and `app/agents/`.

---

## Roadmap

**MVP — delivered**
Repost detection · synthetic discovery · verification agent · action planning ·
human approval · follow-up state machine · escalation tiers · dashboard · APK

**P1**
Real reverse image search · Meta Graph API for the creator's own content ·
deployed weekly scheduler · precision/recall evaluation against the labelled corpus ·
authentication

**P2**
AI likeness-misuse pipeline (InsightFace/ArcFace) · Meta Ad Library discovery ·
multi-platform takedown formats · cross-platform identity linking ·
agent-decision quality evaluation against a human-reviewer baseline

---

*Ditto — An Agentic AI Content Credit System*
