# Reviewer-01 assistance

The owner identified their assignment as reviewer-01 and supplied the completed
reviewer-02 and reviewer-03 JSON exports on 2026-10-21. The source files remain
untouched in Downloads and are not committed to this repository.

`scripts/member_assistance.py` checks each peer export against the exact assignment
and original protected source fields, checks every input image's SHA-256, extracts
frozen MobileNetV3-small features and fits task-specific logistic classifiers to
the peers' examples. Each member also gets a separate example model; disagreement,
score below 0.70 or lack of a majority among three visual reference labels flags
a target suggestion for attention. Scores are uncalibrated.

The generated local assistance covers all 1,017 reviewer-01 records: 518 quality
and 499 maturity. There are 225 quality and 9 maturity attention flags. Each
proposal retains three reference IDs, their supplied labels and reviewer IDs,
visual similarity, model fingerprint and reference-file fingerprints.

This is **not a completed human-reviewed manifest**. `reviewedLabel`,
`reviewedSourceGroup`, `reviewer` and `reviewedAt` remain blank on every target
record. No expert grading rules, physical measurements, source-fruit identities,
human review timestamps or adviser approval are inferred. The assistance helper
uses peer examples from all original candidate partitions, so neither its scores
nor cross-member agreement may be reported as formal held-out model accuracy or
used to justify production deployment. It does not merge or modify peer work.

The private local output folder is `local-review/reviewer-01-ai-2026-10-21/`.
The updated Review Desk accepts the full assistance JSON for both tasks and
validates labels against each record's task. A quality-only file is also retained
for older desk versions. A portable preview with embedded
thumbnails is delivered separately to the owner. All photo/reference artifacts
remain outside public Git.
