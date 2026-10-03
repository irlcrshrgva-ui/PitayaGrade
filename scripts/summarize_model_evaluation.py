"""Summarize complete held-out predictions without inventing missing evidence."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))

_VALIDATOR_PATH = ROOT / 'scripts' / 'validate-research-data.py'
_VALIDATOR_SPEC = importlib.util.spec_from_file_location('pitayagrade_research_validator', _VALIDATOR_PATH)
_VALIDATOR = importlib.util.module_from_spec(_VALIDATOR_SPEC)
_VALIDATOR_SPEC.loader.exec_module(_VALIDATOR)
LABELS = _VALIDATOR.LABELS
validate = _VALIDATOR.validate

PREDICTION_FIELDS = {'model_id', 'sample_id', 'predicted_label', 'confidence', 'inference_ms'}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_predictions(paths):
    rows = []
    file_hashes = []
    for path in paths:
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            missing = PREDICTION_FIELDS - set(reader.fieldnames or ())
            if missing:
                raise ValueError(f'{path}: missing columns: {", ".join(sorted(missing))}')
            rows.extend(dict(row, _source=str(path)) for row in reader)
        file_hashes.append({'path': str(path), 'sha256': sha256(path)})
    return rows, file_hashes


def summarize(manifest, predictions, labels):
    expected = {row['id']: row['reviewedLabel'] for row in manifest
                if row.get('candidateSplit') == 'test'}
    if not expected:
        raise ValueError('Manifest contains no held-out test samples')

    grouped = defaultdict(dict)
    errors = []
    for index, row in enumerate(predictions, 2):
        model_id = (row.get('model_id') or '').strip()
        sample_id = (row.get('sample_id') or '').strip()
        predicted = (row.get('predicted_label') or '').strip()
        source = row.get('_source', '<predictions>')
        if not re.fullmatch(r'[A-Za-z0-9._-]+', model_id):
            errors.append(f'{source}:{index}: invalid model_id')
            continue
        if sample_id not in expected:
            errors.append(f'{source}:{index}: unknown or non-test sample {sample_id!r}')
            continue
        if predicted not in labels:
            errors.append(f'{source}:{index}: incompatible label {predicted!r}')
            continue
        try:
            confidence = float(row.get('confidence', ''))
            latency = float(row.get('inference_ms', ''))
        except ValueError:
            errors.append(f'{source}:{index}: confidence and inference_ms must be numbers')
            continue
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            errors.append(f'{source}:{index}: confidence must be between 0 and 1')
            continue
        if not math.isfinite(latency) or latency < 0:
            errors.append(f'{source}:{index}: inference_ms must be non-negative')
            continue
        if sample_id in grouped[model_id]:
            errors.append(f'{source}:{index}: duplicate prediction for {model_id}/{sample_id}')
            continue
        grouped[model_id][sample_id] = {
            'predicted': predicted, 'confidence': confidence, 'inferenceMs': latency}

    if not grouped:
        errors.append('No valid model predictions supplied')
    for model_id, model_rows in grouped.items():
        missing = sorted(set(expected) - set(model_rows))
        if missing:
            errors.append(f'{model_id}: missing {len(missing)} test predictions; first: {missing[:5]}')
    if errors:
        raise ValueError('\n'.join(errors))

    results = []
    ordered_labels = sorted(labels)
    for model_id in sorted(grouped):
        model_rows = grouped[model_id]
        matrix = {actual: {predicted: 0 for predicted in ordered_labels}
                  for actual in ordered_labels}
        mistakes = []
        latencies = []
        correct = 0
        for sample_id in sorted(expected):
            actual = expected[sample_id]
            prediction = model_rows[sample_id]
            predicted = prediction['predicted']
            matrix[actual][predicted] += 1
            latencies.append(prediction['inferenceMs'])
            if actual == predicted:
                correct += 1
            else:
                mistakes.append({'sampleId': sample_id, 'actual': actual,
                                 'predicted': predicted,
                                 'confidence': prediction['confidence']})

        per_class = {}
        for label in ordered_labels:
            tp = matrix[label][label]
            fp = sum(matrix[actual][label] for actual in ordered_labels if actual != label)
            fn = sum(matrix[label][predicted] for predicted in ordered_labels if predicted != label)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            per_class[label] = {'support': sum(matrix[label].values()), 'precision': precision,
                                'recall': recall, 'f1': f1}
        latencies.sort()
        p95 = latencies[max(0, math.ceil(0.95 * len(latencies)) - 1)]
        results.append({
            'modelId': model_id,
            'sampleCount': len(expected),
            'accuracy': correct / len(expected),
            'macroPrecision': sum(v['precision'] for v in per_class.values()) / len(per_class),
            'macroRecall': sum(v['recall'] for v in per_class.values()) / len(per_class),
            'macroF1': sum(v['f1'] for v in per_class.values()) / len(per_class),
            'meanLatencyMs': sum(latencies) / len(latencies),
            'p95LatencyMs': p95,
            'perClass': per_class,
            'confusionMatrix': matrix,
            'mistakes': mistakes,
        })
    return results


def write_outputs(output_dir, report, labels):
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / 'evaluation.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    with (output_dir / 'summary.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['model_id', 'sample_count', 'accuracy', 'macro_precision',
                         'macro_recall', 'macro_f1', 'mean_latency_ms', 'p95_latency_ms',
                         'mistake_count'])
        for result in report['models']:
            writer.writerow([result['modelId'], result['sampleCount'], result['accuracy'],
                             result['macroPrecision'], result['macroRecall'], result['macroF1'],
                             result['meanLatencyMs'], result['p95LatencyMs'], len(result['mistakes'])])
            model_id = result['modelId']
            with (output_dir / f'confusion-{model_id}.csv').open('w', newline='', encoding='utf-8') as matrix_file:
                matrix_writer = csv.writer(matrix_file)
                matrix_writer.writerow(['actual\\predicted', *labels])
                for actual in labels:
                    matrix_writer.writerow([actual, *[result['confusionMatrix'][actual][p] for p in labels]])
            with (output_dir / f'mistakes-{model_id}.csv').open('w', newline='', encoding='utf-8') as error_file:
                error_writer = csv.DictWriter(error_file,
                                              fieldnames=['sampleId', 'actual', 'predicted', 'confidence'])
                error_writer.writeheader()
                error_writer.writerows(result['mistakes'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, help='Reviewed manifest containing the frozen test split')
    parser.add_argument('predictions', type=Path, nargs='+', help='CSV prediction exports')
    parser.add_argument('--target', choices=LABELS, default='manuscript-quality')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    validation_errors = validate(manifest, args.target, root=ROOT)
    if validation_errors:
        raise SystemExit('Manifest is not evaluation-ready:\n' + '\n'.join(validation_errors[:20]))
    predictions, prediction_files = load_predictions(args.predictions)
    try:
        models = summarize(manifest, predictions, LABELS[args.target])
    except ValueError as error:
        raise SystemExit(f'Predictions are not evaluation-ready:\n{error}') from error
    labels = sorted(LABELS[args.target])
    report = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'target': args.target,
        'manifest': {'path': str(args.manifest), 'sha256': sha256(args.manifest)},
        'predictionFiles': prediction_files,
        'labels': labels,
        'models': models,
        'limitations': ['Metrics describe only the supplied frozen test manifest.',
                        'This report does not establish field performance or clinical diagnosis.'],
    }
    try:
        write_outputs(args.output_dir, report, labels)
    except FileExistsError as error:
        raise SystemExit(f'Output directory already exists: {args.output_dir}') from error
    print(json.dumps({'ready': True, 'models': len(models), 'samplesPerModel': models[0]['sampleCount'],
                      'outputDirectory': str(args.output_dir)}, indent=2))


if __name__ == '__main__':
    main()
