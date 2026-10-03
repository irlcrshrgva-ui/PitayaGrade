# PitayaGrade Week 4 evaluation package

This folder is the evidence handoff for the final evaluation, manuscript revision,
release build and defense. Blank rows are intentional: measured results must come
from the frozen held-out dataset, physical Android devices and actual participants.

## Required order

1. Freeze the model files and record each file's SHA-256 hash.
2. Freeze the reviewed test manifest. Do not tune models or thresholds on it.
3. Complete `model-evaluation-template.csv` for every selectable model and task.
4. Complete `device-test-template.csv` on at least one physical Android device.
5. Resolve release-blocking defects, rebuild, and repeat affected tests.
6. Complete approved user acceptance testing using `uat-template.csv`.
7. Revise the manuscript using only evidence recorded in this folder.

## Evidence rules

- Use the same held-out samples when comparing models for the same task.
- Record failures and excluded samples; do not silently remove them.
- Keep participant identities outside this repository. Use anonymous participant IDs.
- Do not claim disease diagnosis. The app reports visual estimates that require
  physical or expert verification.
- Passing software tests proves runtime behavior, not research accuracy.
- Store large raw exports outside Git and record their path and checksum here.

Quality-model prediction exports should follow `predictions-template.csv`. Use
`python -m scripts.summarize_model_evaluation --help` for the fail-closed comparison
tool; its generated JSON, summary, confusion matrices and mistake lists provide the
source evidence for `model-evaluation-template.csv`.

## Release gate

The capstone is ready for a final release only when:

- reviewed labels cover every required grade and disease class;
- the final model files match the evaluated file hashes;
- per-class results, confusion matrices and failure cases are documented;
- model selection, scanning, records, reports and notifications pass on Android;
- offline first-run, permissions, background/resume and export behavior are tested;
- UAT findings are resolved or explicitly accepted as limitations;
- every manuscript result and figure can be traced to retained evidence.
