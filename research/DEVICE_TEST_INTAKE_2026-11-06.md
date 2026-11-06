# PitayaGrade device-test intake — 6 November 2026

## Source received

- Received file SHA-256: `E03DAA9BA6851D1955BF0A65E73E66A3DB324583C6E72118E149AFBF5D28CD00`
- Rows present: 16/16
- APK SHA-256 recorded in the file: `8018054776c792f5d8af205d6566f2ca8a099d87f9a3b3969f045acfae3f0a96`

The file is preserved as tester input but is not accepted as final release evidence.

## Validation problems

- All `tested_at` values contain `home` instead of a date, time, and timezone.
- `device_model` is `N/A` on every row.
- Status values do not use the required `Pass`, `Fail`, or `Blocked` vocabulary.
- One row has no status.
- Evidence paths and defect references are not usable release evidence.
- The recorded APK checksum does not match the current downloadable build.

## Useful failure observations

| Test | Tester observation | Current automated coverage | Required follow-up |
| --- | --- | --- | --- |
| DT-006 Live-camera scan | Tester believed a photo had to be taken before scanning | Live analysis loop and three-frame stability checks pass; the interface now explains that live estimates update automatically | Retest on the current APK with a real fruit and record a video filename |
| DT-012 Export cancellation and retry | Tester reported cancellation/rejection-export confusion | Android cancellation, retry, and single-picker automated checks pass | Retest the normal records export on the current APK and record the actual saved filename |
| DT-015 Repeated scan taps | Tester reported multiple results | Processing lock and repeated-action automated checks pass | Retest rapid taps on the current APK and confirm one result/record |

Automated checks reduce regression risk but do not replace physical-device evidence. The three affected rows must be retested on the exact new APK. The remaining rows also need valid timestamps, phone details, statuses, and evidence filenames.
