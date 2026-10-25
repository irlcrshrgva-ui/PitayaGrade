# PitayaGrade three-member dataset review guide

This guide divides the 3,050 review records among three people so the work can be
completed independently at home. The assignments do not overlap, and candidate
groups of visually related images remain with one reviewer.

## Before anyone starts

Do not begin final labeling until the adviser has approved, in writing:

- the definitions and visual examples for Grade A, Grade B, Grade C and Reject;
- the rule for Mature Dragon Fruit versus Immature Dragon Fruit;
- who is qualified to review the images;
- how uncertain labels and reviewer disagreements must be resolved; and
- the source-group rule for images showing the same physical fruit or capture
  sequence.

The existing source label and automated source-group suggestion are references,
not proof. A reviewer must inspect every retained image.

## Work allocation

| Member | Reviewer ID | Quality | Maturity | Total |
|---|---:|---:|---:|---:|
| Member 1 | `reviewer-01` | 518 | 499 | 1,017 |
| Member 2 | `reviewer-02` | 518 | 499 | 1,017 |
| Member 3 | `reviewer-03` | 517 | 499 | 1,016 |
| **Total** |  | **1,553** | **1,497** | **3,050** |

Private packages are generated locally under:

`local-review/three-member-packages-2026-10-11/`

The coordinator distributes exactly one ZIP to each member through a private
Google Drive folder, another adviser-approved private service, or a USB drive.
Do not commit the ZIPs or dataset images to the public GitHub repository.

## Three-day fast review plan

The target is about 340 records per member per day. Work in four blocks of about
85 records and take a break between blocks. Accuracy is more important than
finishing a block quickly.

### Day 0 — setup and trial

1. The coordinator sends the approved grading guide and one ZIP to each member.
2. Each member extracts the ZIP to a permanent folder on their own computer.
3. Each member opens the Review Desk and confirms that their assignment and
   approximately 1,016–1,017 local images load.
4. Each member reviews five trial records.
5. The team compares the five decisions and asks the adviser to resolve any
   difference in interpretation before continuing.

### Days 1–3 — production review

Each member reviews approximately 340 records per day:

- Block 1: 85 records
- Block 2: 85 records
- Block 3: 85 records
- Block 4: the remaining daily records

Export a draft backup after every block. At the end of each day, also export the
reviewed manifest and keep both files in a dated private backup folder.

### Day 4 — reconciliation and handoff

1. Every member confirms that both task views show 100% reviewed.
2. Every member exports one final reviewed manifest.
3. The coordinator collects exactly three final JSON exports.
4. The technical workflow merges them with `scripts/merge_review_exports.py`.
5. Any missing, overlapping, modified or incorrectly assigned records cause the
   merge to fail and must be corrected by the responsible reviewer.

For three fully human-reviewed exports, use the strict command:

```powershell
python scripts/merge_review_exports.py --output local-review/final-merged.json <export-1> <export-2> <export-3>
```

If an export intentionally retains `AI-assisted-<reviewer>` attribution, the
coordinator may create a clearly provisional manifest with `--allow-assisted`.
This option preserves the attribution and does not convert AI suggestions into
human ground truth. Such a manifest cannot satisfy the final-review checklist.

After a successful merge, linked records must be placed in one partition:

```powershell
python scripts/reconcile_review_splits.py local-review/final-merged.json --output local-review/training-manifest.json
python scripts/validate-research-data.py local-review/training-manifest.json --target manuscript-quality
```

Run validation separately for each task when one file contains both quality and
maturity records. Conflicting labels inside one source-fruit group require human
adjudication; the validator rejects them rather than choosing a label.

## Instructions for every reviewer

1. Extract only your assigned ZIP. Do not exchange records with another member.
2. Open the hosted Review Desk:
   <https://irlcrshrgva-ui.github.io/PitayaGrade/review-tool/index.html>
3. If **Member assignment** is not visible, refresh the page with `Ctrl+F5`.
4. Under **Member assignment**, select the reviewer ID written on your ZIP.
5. Click **Load local dataset folder** and select the extracted package folder.
   The images remain on your computer; selecting the folder does not add them to
   the GitHub repository.
6. Confirm that the page reports the expected number of local images.
7. Select **Quality grading** and **Unreviewed first**.
8. For every image:
   - inspect the image itself;
   - select the label using only the approved grading guide;
   - enter or confirm the source-fruit group;
   - click **Save review & next**.
9. After finishing Quality grading, switch to **Maturity** and repeat the process.
10. Use **Export draft backup** after every work block. Use **Restore draft
    backup** if browser progress is lost.
11. When both tasks reach 100%, click **Export reviewed manifest** and send that
    final JSON file to the coordinator.

Use the same browser and computer throughout the review. Do not use a private or
incognito window, clear browser/site data, or depend on browser storage without
exporting backups.

## Source-fruit group decision rule

- Use the same group ID only when the images genuinely appear to show the same
  physical fruit or the same capture sequence.
- A visually similar suggestion is only a prompt to compare the images. It is
  never automatically confirmed.
- If images are clearly different, give them different group IDs.
- If identity is uncertain, do not guess. Export a backup, record the affected
  record ID and ask the coordinator/adviser to adjudicate it.

This rule matters because images from one physical fruit must not be separated
between training and final evaluation sets.

## Label decision rule

- Never copy the displayed source label without inspecting the image.
- Never use a model proposal as the final answer without human confirmation.
- Do not invent a grade when the approved guide does not cover the case.
- Record an uncertain item for adviser adjudication before saving it.
- Do not change another member's assignment or reviewer ID.

## Coordinator checklist

- [ ] Obtain and distribute the adviser-approved grading guide.
- [ ] Send one private ZIP to each member.
- [ ] Confirm every member can load their assignment and images.
- [ ] Complete the five-record calibration exercise.
- [ ] Collect a backup from every member after each day.
- [ ] Confirm Quality and Maturity both show 100% for every member.
- [ ] Collect exactly three final reviewed-manifest JSON files.
- [ ] Preserve reviewer IDs and timestamps.
- [ ] Merge the exports with the strict merge validator.
- [ ] Resolve every merge error instead of bypassing validation.
- [ ] Keep the raw exports as research evidence and create two private backups.
- [ ] Return the merged manifest for model training and formal evaluation.

## What is and is not on GitHub

The public repository contains the Review Desk source, assignment index,
validation scripts and this guide. GitHub Pages hosts the Review Desk interface.
The 374 MB image dataset, members' browser progress and final review exports are
not published. Those files must remain in the team's controlled private storage.

## AI-assisted recheck packages

If a provisional merge retains rows attributed to `AI-assisted-<reviewer>`, create
private three-member confirmation packages with:

```powershell
python scripts/create_assisted_recheck_packages.py --manifest <validated-provisional-manifest.json> --output <private-output-folder>
```

Each member extracts one ZIP, opens the current Review Desk, loads
`assignment-index.json` through **Load recheck assignment**, selects their
`recheck-XX` assignment, restores `draft-backup.json`, loads the extracted image
folder, and chooses **All AI-assisted labels**. Saving a checked record replaces
its AI-assisted attribution with the human recheck reviewer. Both task queues
must reach zero before the member exports their reviewed manifest.

After collecting all recheck exports, the coordinator freezes the human-reviewed
manifest in one fail-closed step:

```powershell
python scripts/finalize_rechecks.py <recheck-01.json> <recheck-02.json> <recheck-03.json> `
  --base <validated-provisional-manifest.json> `
  --assignments <recheck-package-folder/assignment-index.json> `
  --output-dir <new-private-final-folder>
```

The command refuses missing assignments, AI-assisted attribution, changed image
identity, invalid labels/timestamps, conflicts, and split leakage. It produces a
frozen training manifest plus a checksum-bearing finalization audit.

## Finalizing the three disease-annotation exports

After all disease-annotation members finish, merge their exports against the
original crop manifest and the exact assignment index:

```powershell
python scripts/finalize_disease_annotations.py <mask-reviewer-01.json> <mask-reviewer-02.json> <mask-reviewer-03.json> `
  --base <original-crop-manifest.json> `
  --assignments <annotation-package-folder/assignment-index.json> `
  --output-dir <new-private-final-folder>
```

The command refuses missing or overlapping assignments, changed record identity
or checksums, incorrect reviewer IDs, malformed polygons, split leakage, and
incomplete class coverage. Use only the generated
`frozen-disease-annotation-manifest.json` for final segmentation training and
retain `annotation-finalization-audit.json` with the private evidence.

