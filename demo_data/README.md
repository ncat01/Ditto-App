# Demo data

`ground_truth.json` is the labelled synthetic corpus used by both the Android app and
the backend. Every candidate carries a recorded `groundTruth` label, which is what makes
precision/recall and agent-decision quality measurable.

| Label | Count | Purpose |
|-------|-------|---------|
| `genuine_repost` | 4 | True positives, each with a different transformation |
| `false_positive` | 1 | Coincidental similarity, to measure false-positive rate |
| `genuine_likeness_misuse` | 1 | Face match without a frame match (P2 architecture) |

Positive examples use the transformations the project report proposes: crop, watermark,
re-encode, aspect-ratio change and caption overlay.

The live copy is served at `GET /api/demo/ground-truth`.
