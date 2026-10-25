"""Generate manuscript-ready summaries only from a passing, hash-bound Week 4 audit."""
import argparse
import csv
import hashlib
import html
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

EVIDENCE_FILES = ('model-evaluation.csv', 'device-test.csv', 'uat.csv')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def percent(value):
    return f'{float(value) * 100:.1f}%'


def decimal(value, places=1):
    return f'{float(value):.{places}f}'


def markdown_table(headers, rows):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')
    lines = ['| ' + ' | '.join(map(cell, headers)) + ' |',
             '| ' + ' | '.join('---' for _ in headers) + ' |']
    lines.extend('| ' + ' | '.join(cell(value) for value in row) + ' |' for row in rows)
    return '\n'.join(lines)


def bar_svg(title, rows, output):
    width, label_width, chart_width = 820, 250, 500
    height = 90 + 42 * len(rows)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#071f19"/>',
             f'<text x="24" y="38" fill="#f7fff9" font-family="Arial" font-size="22" font-weight="700">{html.escape(title)}</text>']
    for index, (label, value, color) in enumerate(rows):
        y = 70 + index * 42
        value = max(0.0, min(1.0, float(value)))
        parts.extend([
            f'<text x="24" y="{y + 19}" fill="#d6efe5" font-family="Arial" font-size="14">{html.escape(label)}</text>',
            f'<rect x="{label_width}" y="{y}" width="{chart_width}" height="24" rx="5" fill="#163c32"/>',
            f'<rect x="{label_width}" y="{y}" width="{chart_width * value:.2f}" height="24" rx="5" fill="{color}"/>',
            f'<text x="{label_width + chart_width + 12}" y="{y + 18}" fill="#f7fff9" font-family="Arial" font-size="14">{value * 100:.1f}%</text>'
        ])
    parts.append('</svg>')
    Path(output).write_text('\n'.join(parts) + '\n', encoding='utf-8')


def verify_audit(evidence_dir, audit_path):
    audit = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    if audit.get('status') != 'pass' or audit.get('errors') != []:
        raise ValueError('Week 4 evidence audit is not passing')
    for name in EVIDENCE_FILES:
        path = Path(evidence_dir) / name
        record = audit.get('files', {}).get(name, {})
        if not path.is_file() or record.get('sha256') != sha256(path) or int(record.get('rows', 0)) < 1:
            raise ValueError(f'{name} no longer matches the passing evidence audit')
    return audit


def generate(evidence_dir, audit_path, output_dir):
    evidence_dir, output_dir = Path(evidence_dir), Path(output_dir)
    if output_dir.exists():
        raise FileExistsError('Output directory already exists; choose a new path')
    audit = verify_audit(evidence_dir, audit_path)
    models = read_csv(evidence_dir / 'model-evaluation.csv')
    devices = read_csv(evidence_dir / 'device-test.csv')
    uat = read_csv(evidence_dir / 'uat.csv')
    output_dir.mkdir(parents=True)

    quality = sorted((row for row in models if row['task'] == 'quality'), key=lambda row: row['model_id'])
    disease = sorted((row for row in models if row['task'] == 'disease'), key=lambda row: row['model_id'])
    model_report = ['# Final model evaluation', '',
        'Generated from the checksum-validated Week 4 evidence package.', '',
        '## Quality models', '',
        markdown_table(['Model', 'Accuracy', 'Macro precision', 'Macro recall', 'Macro F1', 'Mean latency', 'P95 latency'], [
            [row['model_name'], percent(row['accuracy']), percent(row['macro_precision']),
             percent(row['macro_recall']), percent(row['macro_f1']),
             f"{decimal(row['mean_latency_ms'])} ms", f"{decimal(row['p95_latency_ms'])} ms"]
            for row in quality]), '', '## Disease segmentation models', '',
        markdown_table(['Model', 'mAP50', 'mAP50–95', 'Mask mAP50', 'Mean latency', 'P95 latency'], [
            [row['model_name'], percent(row['map50']), percent(row['map50_95']), percent(row['mask_map50']),
             f"{decimal(row['mean_latency_ms'])} ms", f"{decimal(row['p95_latency_ms'])} ms"]
            for row in disease]), '']
    (output_dir / 'model-results.md').write_text('\n'.join(model_report), encoding='utf-8')
    model_bars = [(f"{row['model_name']} accuracy", row['accuracy'], '#55d6a9') for row in quality]
    model_bars += [(f"{row['model_name']} macro F1", row['macro_f1'], '#ff4f91') for row in quality]
    bar_svg('Quality model held-out results', model_bars, output_dir / 'quality-model-results.svg')
    disease_bars = []
    for row in disease:
        disease_bars.extend([(f"{row['model_name']} mAP50", row['map50'], '#55d6a9'),
                             (f"{row['model_name']} mAP50–95", row['map50_95'], '#ffca58'),
                             (f"{row['model_name']} mask mAP50", row['mask_map50'], '#ff4f91')])
    bar_svg('Disease segmentation held-out results', disease_bars,
            output_dir / 'disease-model-results.svg')

    by_device = defaultdict(list)
    for row in devices:
        by_device[(row['device_model'], row['android_version'])].append(row)
    device_rows = [[model, android, len(items), sum(item['status'].lower() == 'pass' for item in items)]
                   for (model, android), items in sorted(by_device.items())]
    device_report = ['# Android device-test summary', '',
        f'**Distinct devices:** {len(by_device)}  ', f'**Test runs:** {len(devices)}  ',
        f"**Passed runs:** {sum(row['status'].lower() == 'pass' for row in devices)}", '',
        markdown_table(['Device', 'Android version', 'Runs', 'Passed'], device_rows), '']
    (output_dir / 'device-test-summary.md').write_text('\n'.join(device_report), encoding='utf-8')

    participant_count = len({row['participant_id'] for row in uat})
    completed = sum(row['completed'].lower() == 'true' for row in uat)
    ease = [float(row['ease_rating_1_to_5']) for row in uat]
    confidence = [float(row['confidence_rating_1_to_5']) for row in uat]
    times = [float(row['time_seconds']) for row in uat]
    task_counts = Counter(row['task_id'] for row in uat)
    uat_report = ['# User acceptance testing summary', '',
        f'**Participants:** {participant_count}  ', f'**Task sessions:** {len(uat)}  ',
        f'**Completion rate:** {completed / len(uat) * 100:.1f}%  ',
        f'**Mean ease rating:** {statistics.fmean(ease):.2f}/5  ',
        f'**Mean confidence rating:** {statistics.fmean(confidence):.2f}/5  ',
        f'**Median task time:** {statistics.median(times):.1f} seconds', '',
        markdown_table(['Task', 'Sessions'], sorted(task_counts.items())), '']
    (output_dir / 'uat-summary.md').write_text('\n'.join(uat_report), encoding='utf-8')
    bar_svg('User acceptance results', [
        ('Task completion', completed / len(uat), '#55d6a9'),
        ('Ease rating', statistics.fmean(ease) / 5, '#ffca58'),
        ('Confidence rating', statistics.fmean(confidence) / 5, '#ff4f91')],
        output_dir / 'uat-results.svg')

    outputs = sorted(path for path in output_dir.iterdir() if path.name != 'traceability.json')
    traceability = {
        'status': 'generated-from-validated-evidence',
        'evidenceAudit': {'path': str(audit_path), 'sha256': sha256(audit_path),
                          'generatedAt': audit.get('generatedAt')},
        'inputs': {name: {'path': str(evidence_dir / name), 'sha256': sha256(evidence_dir / name)}
                   for name in EVIDENCE_FILES},
        'outputs': {path.name: sha256(path) for path in outputs},
    }
    (output_dir / 'traceability.json').write_text(json.dumps(traceability, indent=2) + '\n', encoding='utf-8')
    return traceability


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    parser.add_argument('--audit', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        report = generate(args.evidence_dir, args.audit, args.output_dir)
    except (OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
