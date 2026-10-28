"""Create blank, APK-bound Android and UAT worksheets without inventing results."""
import argparse
import csv
import hashlib
from pathlib import Path


DEVICE_FIELDS = [
    'test_run_id', 'tested_at', 'device_model', 'android_version', 'app_version',
    'apk_sha256', 'network_state', 'test_case', 'precondition', 'steps',
    'expected_result', 'actual_result', 'status', 'evidence_path', 'defect_id', 'tester',
]
UAT_FIELDS = [
    'session_id', 'tested_at', 'participant_id', 'participant_role', 'device_model',
    'app_version', 'task_id', 'task_description', 'completed', 'time_seconds',
    'error_count', 'help_needed', 'ease_rating_1_to_5', 'confidence_rating_1_to_5',
    'participant_comment', 'observer_note', 'issue_id',
]

DEVICE_CASES = [
    ('offline', 'Clean install and offline first run', 'App is not installed; airplane mode is enabled',
     'Install the APK, launch it, dismiss the tutorial, and open Scan',
     'The app opens without a network connection and clearly reports available models'),
    ('online', 'Camera permission denied', 'App is installed; camera permission is not granted',
     'Open live camera, deny permission, then return to Scan',
     'A clear permission message appears and the app remains usable'),
    ('online', 'Camera permission granted', 'Camera permission is available',
     'Open live camera and grant permission',
     'The preview opens and can be stopped without leaving the camera active'),
    ('offline', 'Gallery scan with a clear dragon fruit', 'A clear test image is stored on the phone',
     'Choose Photo, select the image, and run the scan',
     'The app shows a reviewable result or an honest rejection with model identity'),
    ('offline', 'Gallery scan with a non-fruit image', 'A non-dragon-fruit image is stored on the phone',
     'Choose Photo, select the image, and run the scan',
     'The image is rejected instead of being saved as a confident dragon-fruit grade'),
    ('offline', 'Live-camera dragon-fruit scan', 'Camera permission is granted and a fruit is available',
     'Open Live Camera, frame one fruit clearly, and scan',
     'The scan completes once and displays a reviewable result or honest rejection'),
    ('offline', 'Model selector and persistence', 'At least one verified model is available',
     'Open Settings, select every available model in turn, close and reopen the app',
     'Only verified models are selectable and the last valid choice persists'),
    ('offline', 'Save scan record', 'A scan result is visible',
     'Save the result, including a human validation value when applicable',
     'The record appears once in History with model and method information'),
    ('offline', 'History search and note', 'At least one saved record exists',
     'Find the record with search, add a note, leave History, and return',
     'The correct record is found and its note persists'),
    ('offline', 'Analytics and date-bounded report', 'Saved records cover the selected date range',
     'Open analytics, create a report for the range, and review totals',
     'Totals match the saved records and the report identifies its date range'),
    ('offline', 'Notification preference and read state', 'At least one new scan alert can be produced',
     'Toggle scan alerts, create an alert, mark it read, and reopen notifications',
     'The preference and read state persist without duplicating alerts'),
    ('offline', 'CSV export, cancellation, and retry', 'At least one record exists',
     'Start export, cancel the save dialog, then retry and save the CSV',
     'Cancellation is quiet and retry creates a readable CSV exactly once'),
    ('offline', 'Background and resume', 'A scan or report screen is open',
     'Send the app to the background for 30 seconds and resume it',
     'The app resumes without a frozen camera, duplicate result, or lost saved data'),
    ('offline', 'Rotation and interrupted scan', 'Auto-rotate is enabled',
     'Start a scan, rotate the device, navigate away, then return',
     'The interface remains usable and no abandoned camera stream continues'),
    ('offline', 'Repeated scan taps', 'A valid image is selected',
     'Tap the analyze control repeatedly in quick succession',
     'Only one analysis and one saved result are produced'),
    ('offline', 'Force-stop and device restart', 'Saved records and settings exist',
     'Force-stop the app, reopen it, restart the phone, and reopen it again',
     'Saved records and valid settings remain available after both restarts'),
]

UAT_TASKS = [
    ('UAT-01', 'Choose an available analysis model'),
    ('UAT-02', 'Upload or capture a clear dragon-fruit image and start a scan'),
    ('UAT-03', 'Explain the result, confidence, and visible limitation shown'),
    ('UAT-04', 'Find the saved result in History'),
    ('UAT-05', 'Add and save a note on the record'),
    ('UAT-06', 'Open analytics and prepare a date-bounded report'),
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, fields, rows):
    with Path(path).open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def create_pack(output_dir, apk, app_version):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('Output directory must be empty; existing testing evidence is never overwritten')
    output_dir.mkdir(parents=True, exist_ok=True)
    digest = sha256(apk)
    device_rows = []
    for index, (network, test_case, precondition, steps, expected) in enumerate(DEVICE_CASES, 1):
        row = {field: '' for field in DEVICE_FIELDS}
        row.update({
            'test_run_id': f'DT-{index:03d}', 'app_version': app_version,
            'apk_sha256': digest, 'network_state': network, 'test_case': test_case,
            'precondition': precondition, 'steps': steps, 'expected_result': expected,
        })
        device_rows.append(row)
    uat_rows = []
    for task_id, description in UAT_TASKS:
        row = {field: '' for field in UAT_FIELDS}
        row.update({'app_version': app_version, 'task_id': task_id, 'task_description': description})
        uat_rows.append(row)
    write_csv(output_dir / 'device-test.csv', DEVICE_FIELDS, device_rows)
    write_csv(output_dir / 'uat.csv', UAT_FIELDS, uat_rows)
    (output_dir / 'README.txt').write_text(
        'PitayaGrade supervised testing pack\n'
        f'App version: {app_version}\nAPK SHA-256: {digest}\n\n'
        'These worksheets are BLANK PLANS, not completed evidence.\n'
        'Device testing: fill tested_at with a timezone, device and Android details, actual_result, '
        'status, evidence_path, and tester for every row. Use Pass, Fail, or Blocked exactly.\n'
        'UAT: obtain adviser approval and any required consent first. Duplicate the six task rows for '
        'each anonymous participant, then fill every measurement from direct observation.\n'
        'Never invent results or participant responses. Keep personal identities outside the repository.\n',
        encoding='utf-8')
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--apk', required=True, type=Path)
    parser.add_argument('--app-version', default='1.0.0-testing')
    args = parser.parse_args()
    if not args.apk.is_file():
        parser.error('APK file does not exist')
    try:
        digest = create_pack(args.output_dir, args.apk, args.app_version)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'Created blank testing pack for APK SHA-256 {digest}')


if __name__ == '__main__':
    main()
