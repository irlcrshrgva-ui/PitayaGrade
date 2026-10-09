# What the PitayaGrade team must do next

This handoff starts after the autonomous software work recorded on 10 October
2026. Complete the steps in order. Do not train or report accuracy before Steps 1
through 3 are approved.

## Step 1 — Obtain adviser decisions

Ask the adviser to approve, in writing:

- the definitions for Grade A, Grade B, Grade C and Reject;
- the visible disease/symptom classes and mask rules;
- who is qualified to review quality labels and disease masks;
- the minimum number of Android devices and UAT participants;
- the evaluation metrics and acceptance criteria;
- the consent/privacy procedure for UAT.

Save the approval or meeting record with the project evidence. Do not replace an
adviser decision with an AI-generated definition.

## Step 2 — Review possible source groups first

On the project computer, start the private review tool:

```powershell
node scripts/serve-review.js
```

Open `http://127.0.0.1:4174`, then choose **Load source-group suggestions** and
select:

`research/source-group-suggestions-2026-10-10.json`

Inspect the suggested images. Start with groups marked **crosses candidate
splits**. Use one source group only when the images genuinely show the same
physical fruit or capture sequence. The suggestion is not proof and is never
saved automatically.

## Step 3 — Review the labels

In the same Review Desk:

1. Enter an anonymous reviewer ID.
2. Inspect the image rather than copying its original public label.
3. Select the adviser-approved target label.
4. Enter the confirmed source-fruit group.
5. Save and continue.
6. Export a JSON backup at the end of every work session.

If several people review the data, assign non-overlapping records and keep their
exports separate. Preserve reviewer IDs and timestamps. Resolve disagreements
through the adviser-approved procedure.

After review, export the complete reviewed manifest and run:

```powershell
python scripts/validate-research-data.py PATH_TO_REVIEWED_MANIFEST --target manuscript-quality
```

Do not continue until it passes and all same-source images occupy one split.

## Step 4 — Return the reviewed evidence

Provide these files to the technical workflow:

- the approved class/annotation guide;
- the completed reviewed quality manifest;
- the reviewed detection boxes, if detection retraining is required;
- the reviewed disease masks and Healthy negative records;
- the adviser-approved evaluation protocol.

At that point the automated workflow can train MobileNetV2, ResNet50,
EfficientNet-B3 and YOLOv8-Nano segmentation; export ONNX assets; calculate held-out
metrics; integrate passing models; and generate final manuscript figures.

## Step 5 — Test the actual Android application

After the evaluated models are integrated:

1. Install the exact candidate APK on every approved phone.
2. Record the phone model, Android version and APK checksum.
3. Test permission handling, photo upload and live camera.
4. Test clear fruit images and real negative scenes such as faces, hands, empty
   backgrounds and unrelated objects.
5. Test offline startup/inference, history, notifications, reports and CSV export.
6. Record every run in `research/week4/device-test-template.csv` or its approved
   completed copy.
7. Report defects before repeating failed cases.

Screenshots alone are not sufficient; preserve the completed device-test rows.

## Step 6 — Conduct approved UAT

Use the adviser-approved participants and procedure. Do not invent participant
ratings or coach participants through the tasks. Preserve completed task results,
comments and consent records where required. Start from
`research/week4/uat-template.csv`.

## Step 7 — Finish the submission

When reviewed predictions, device tests and UAT are complete:

- regenerate model tables, confusion matrices and segmentation figures;
- update Chapter 5, the abstract, conclusions and defense deck;
- obtain the team-controlled Android signing key outside Git;
- build and install the signed release;
- record its version and SHA-256 checksum;
- tag the final Git commit and create two submission backups;
- obtain final adviser approval.

## Files to send back for technical completion

The minimum useful handoff is:

1. reviewed quality manifest;
2. reviewed disease/detection annotations;
3. approved evaluation protocol;
4. completed device-test CSV;
5. completed UAT CSV;
6. signing access provided securely by the project owner when the release is ready.

