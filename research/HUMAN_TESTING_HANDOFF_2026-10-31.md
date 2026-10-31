# PitayaGrade human-testing handoff — 31 October 2026

## Exact testing build

- Website: <https://irlcrshrgva-ui.github.io/PitayaGrade/site/testing.html>
- APK: <https://irlcrshrgva-ui.github.io/PitayaGrade/downloads/PitayaGrade-debug.apk>
- Version: `1.0.0-testing`
- Source commit: `e32aaa42474d0c06592bbc2e772cb080b01635b0`
- APK SHA-256: `4411b47156fd8a47ff7fd0008bbdce95fa20bd2c38c571104bfbf5681f23f748`
- APK size: 167,949,482 bytes
- Build time: `2026-10-31T05:59:36Z`
- Signing status: debug testing build; not the final signed release

Every tester must download the APK and worksheets from the testing page above.
Do not reuse a worksheet generated for an older APK checksum.

## Three-member device plan

Each member should run all 16 rows on one Android phone. Splitting the rows across
members would leave some device/scenario combinations untested.

| Member | Anonymous tester ID | Device work |
|---|---|---|
| Member 1 / coordinator | `tester-01` | Run all 16 tests on Phone A |
| Member 2 | `tester-02` | Run all 16 tests on Phone B |
| Member 3 | `tester-03` | Run all 16 tests on Phone C |

If only one phone is available, complete one honest 16-row pilot and record that
the device matrix contains one device. Do not copy a passing result to another
phone or tester.

## For every device-test row

1. Record the phone model, Android version, network state, date/time with time zone,
   anonymous tester ID, and the APK SHA-256 above.
2. Follow the listed precondition and steps without changing the expected result.
3. Write what actually happened.
4. Choose `Pass`, `Fail`, or `Blocked`.
5. Save a screenshot or short recording and enter its private evidence path.
6. Give every failure a defect ID such as `BUG-01`.
7. Keep the original failed row. Add a new retest row after a corrected build.

Use a real fruit for live-camera testing. A photo displayed on another screen may
be used as an additional robustness check, but it does not replace the real-fruit
camera test.

## UAT plan

The published UAT worksheet contains six tasks. Duplicate all six task rows for
every adviser-approved participant. Use anonymous IDs and record task completion,
time, errors, help required, ease, confidence, comments, and observer notes.
Do not coach a participant through the interface. Keep names, consent forms, and
other private information outside the public repository.

## Return package

Send the coordinator:

- one completed device CSV per phone;
- one completed UAT CSV covering all approved participants;
- the private screenshot/video folder;
- a short defect list showing open and retested issues; and
- adviser confirmation of the required device and participant counts.

These files are human evidence. Blank templates, copied rows, automated tests, and
AI-generated observations cannot replace them.
