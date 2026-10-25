"""Validate final model, Android-device, and UAT CSV evidence before release."""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

FILES = {
    'model-evaluation.csv': {'evaluation_id', 'evaluated_at', 'task', 'model_name', 'model_version',
        'model_id', 'model_path', 'model_sha256', 'test_manifest', 'test_manifest_sha256', 'test_sample_count', 'classes',
        'input_size', 'device', 'runtime', 'failed_samples', 'confusion_matrix_path',
        'predictions_path', 'reviewer'},
    'device-test.csv': {'test_run_id', 'tested_at', 'device_model', 'android_version', 'app_version',
        'apk_sha256', 'network_state', 'test_case', 'precondition', 'steps', 'expected_result',
        'actual_result', 'status', 'evidence_path', 'tester'},
    'uat.csv': {'session_id', 'tested_at', 'participant_id', 'participant_role', 'device_model',
        'app_version', 'task_id', 'task_description', 'completed', 'time_seconds', 'error_count',
        'help_needed', 'ease_rating_1_to_5', 'confidence_rating_1_to_5', 'participant_comment',
        'observer_note'},
}
SHA256 = re.compile(r'^[0-9a-fA-F]{64}$')
EXPECTED_MODELS = {
    'yolov8-nano': 'quality',
    'mobilenetv2-quality': 'quality',
    'resnet50-quality': 'quality',
    'efficientnet-b3-quality': 'quality',
    'yolov8n-disease-seg': 'disease',
}
PREDICTION_FIELDS = {'model_id', 'sample_id', 'predicted_label', 'confidence', 'inference_ms'}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path, required):
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f'{path}: missing columns: {", ".join(sorted(missing))}')
        rows = list(reader)
    if not rows:
        raise ValueError(f'{path}: no evidence rows')
    return rows


def timestamp(value, context, errors):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError
    except (TypeError, ValueError):
        errors.append(f'{context}: timestamp must include a timezone')


def number(value, context, errors, minimum=0, maximum=None, integer=False):
    try:
        parsed = int(value) if integer else float(value)
        if not math.isfinite(parsed) or parsed < minimum or (maximum is not None and parsed > maximum):
            raise ValueError
    except (TypeError, ValueError):
        errors.append(f'{context}: invalid numeric value {value!r}')


def evidence_path(directory, value):
    path = Path(value)
    return path if path.is_absolute() else Path(directory) / path


def validate_model(rows, errors, directory):
    tasks, identities, models = set(), set(), set()
    for index, row in enumerate(rows, 2):
        context = f'model-evaluation.csv:{index}'
        identity = row['evaluation_id'].strip()
        if not identity or identity in identities:
            errors.append(f'{context}: missing or duplicate evaluation_id')
        identities.add(identity)
        timestamp(row['evaluated_at'], context, errors)
        task = row['task'].strip()
        if task not in ('quality', 'disease'):
            errors.append(f'{context}: task must be quality or disease')
        tasks.add(task)
        model_id = row['model_id'].strip()
        if model_id not in EXPECTED_MODELS or EXPECTED_MODELS.get(model_id) != task:
            errors.append(f'{context}: unexpected model_id/task combination')
        if model_id in models:
            errors.append(f'{context}: duplicate model_id')
        models.add(model_id)
        for field in ('model_name', 'model_version', 'model_path', 'test_manifest', 'classes', 'device', 'runtime',
                      'confusion_matrix_path', 'predictions_path', 'reviewer'):
            if not row[field].strip():
                errors.append(f'{context}: {field} is required')
        for field in ('model_sha256', 'test_manifest_sha256'):
            if not SHA256.fullmatch(row[field].strip()):
                errors.append(f'{context}: {field} must be SHA-256')
        for field in ('test_sample_count', 'input_size'):
            number(row[field], f'{context}:{field}', errors, minimum=1, integer=True)
        number(row['failed_samples'], f'{context}:failed_samples', errors, minimum=0, integer=True)
        if row['failed_samples'].strip() != '0':
            errors.append(f'{context}: failed_samples must be zero for release')
        for field in ('mean_latency_ms', 'p95_latency_ms'):
            number(row.get(field), f'{context}:{field}', errors, minimum=0)
        metric_fields = ('accuracy', 'macro_precision', 'macro_recall', 'macro_f1') if task == 'quality' else (
            'map50', 'map50_95', 'mask_map50')
        for field in metric_fields:
            number(row.get(field), f'{context}:{field}', errors, minimum=0, maximum=1)
        model_path = evidence_path(directory, row['model_path'])
        manifest_path = evidence_path(directory, row['test_manifest'])
        confusion_path = evidence_path(directory, row['confusion_matrix_path'])
        predictions_path = evidence_path(directory, row['predictions_path'])
        for label, path in (('model_path', model_path), ('test_manifest', manifest_path),
                            ('confusion_matrix_path', confusion_path), ('predictions_path', predictions_path)):
            if not path.is_file():
                errors.append(f'{context}: {label} does not exist: {path}')
        if model_path.is_file() and file_hash(model_path).lower() != row['model_sha256'].strip().lower():
            errors.append(f'{context}: model_sha256 does not match model_path')
        if manifest_path.is_file() and file_hash(manifest_path).lower() != row['test_manifest_sha256'].strip().lower():
            errors.append(f'{context}: test_manifest_sha256 does not match test_manifest')
        if predictions_path.is_file():
            try:
                prediction_rows = read_csv(predictions_path, PREDICTION_FIELDS)
                expected_count = int(row['test_sample_count'])
                if len(prediction_rows) != expected_count:
                    errors.append(f'{context}: predictions row count does not match test_sample_count')
                if any(item['model_id'].strip() != model_id for item in prediction_rows):
                    errors.append(f'{context}: predictions contain a different model_id')
                sample_ids = [item['sample_id'].strip() for item in prediction_rows]
                if any(not item for item in sample_ids) or len(sample_ids) != len(set(sample_ids)):
                    errors.append(f'{context}: predictions need unique non-empty sample IDs')
            except (OSError, ValueError, csv.Error) as error:
                errors.append(f'{context}: invalid predictions evidence: {error}')
    if not {'quality', 'disease'} <= tasks:
        errors.append('model-evaluation.csv: both quality and disease evaluations are required')
    missing_models = sorted(set(EXPECTED_MODELS) - models)
    if missing_models:
        errors.append(f'model-evaluation.csv: missing selectable models: {", ".join(missing_models)}')


def validate_devices(rows, errors, minimum_devices):
    devices, runs = set(), set()
    for index, row in enumerate(rows, 2):
        context = f'device-test.csv:{index}'
        run = row['test_run_id'].strip()
        if not run or run in runs:
            errors.append(f'{context}: missing or duplicate test_run_id')
        runs.add(run)
        timestamp(row['tested_at'], context, errors)
        for field in FILES['device-test.csv'] - {'test_run_id', 'tested_at'}:
            if not row.get(field, '').strip():
                errors.append(f'{context}: {field} is required')
        if not SHA256.fullmatch(row['apk_sha256'].strip()):
            errors.append(f'{context}: apk_sha256 must be SHA-256')
        status = row['status'].strip().lower()
        if status not in ('pass', 'fail', 'blocked'):
            errors.append(f'{context}: status must be pass, fail, or blocked')
        if status != 'pass':
            errors.append(f'{context}: unresolved {status or "unknown"} result blocks release')
        devices.add((row['device_model'].strip(), row['android_version'].strip()))
    if len(devices) < minimum_devices:
        errors.append(f'device-test.csv: requires at least {minimum_devices} distinct devices; found {len(devices)}')


def validate_uat(rows, errors, minimum_participants):
    participants, sessions = set(), set()
    for index, row in enumerate(rows, 2):
        context = f'uat.csv:{index}'
        session = row['session_id'].strip()
        if not session or session in sessions:
            errors.append(f'{context}: missing or duplicate session_id')
        sessions.add(session)
        timestamp(row['tested_at'], context, errors)
        for field in FILES['uat.csv'] - {'participant_comment', 'observer_note'}:
            if not row.get(field, '').strip():
                errors.append(f'{context}: {field} is required')
        if row['completed'].strip().lower() not in ('true', 'false'):
            errors.append(f'{context}: completed must be true or false')
        for field in ('time_seconds', 'error_count'):
            number(row[field], f'{context}:{field}', errors, minimum=0, integer=True)
        if row['help_needed'].strip().lower() not in ('true', 'false'):
            errors.append(f'{context}: help_needed must be true or false')
        for field in ('ease_rating_1_to_5', 'confidence_rating_1_to_5'):
            number(row[field], f'{context}:{field}', errors, minimum=1, maximum=5, integer=True)
        participants.add(row['participant_id'].strip())
    if len(participants) < minimum_participants:
        errors.append(f'uat.csv: requires at least {minimum_participants} participants; found {len(participants)}')


def validate_evidence(directory, minimum_devices=1, minimum_participants=1):
    directory = Path(directory)
    rows = {name: read_csv(directory / name, fields) for name, fields in FILES.items()}
    errors = []
    validate_model(rows['model-evaluation.csv'], errors, directory)
    validate_devices(rows['device-test.csv'], errors, minimum_devices)
    validate_uat(rows['uat.csv'], errors, minimum_participants)
    return {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'status': 'pass' if not errors else 'blocked',
        'minimumDevices': minimum_devices,
        'minimumParticipants': minimum_participants,
        'files': {name: {'sha256': file_hash(directory / name), 'rows': len(value)}
                  for name, value in rows.items()},
        'modelAssets': {row['model_id']: {
            'sha256': row['model_sha256'].lower(),
            'path': str(evidence_path(directory, row['model_path']).resolve()),
        } for row in rows['model-evaluation.csv']},
        'deviceCount': len({(row['device_model'], row['android_version']) for row in rows['device-test.csv']}),
        'participantCount': len({row['participant_id'] for row in rows['uat.csv']}),
        'errors': errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    parser.add_argument('--min-devices', type=int, default=1)
    parser.add_argument('--min-participants', type=int, default=1)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.min_devices < 1 or args.min_participants < 1:
        parser.error('Minimum devices and participants must be positive')
    if args.output.exists():
        parser.error('Output audit already exists; choose a new path')
    try:
        report = validate_evidence(args.evidence_dir, args.min_devices, args.min_participants)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError, KeyError, csv.Error) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    if report['errors']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
