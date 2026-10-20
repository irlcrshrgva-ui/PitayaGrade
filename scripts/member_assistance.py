"""Generate traceable AI proposals from peer examples, never human-review evidence."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from scripts.train_disease import preprocessing
from scripts.mendeley_disease import file_hash

ROOT = Path(__file__).resolve().parents[1]
REVIEW_FIELDS = {'reviewedLabel', 'reviewedSourceGroup', 'reviewer', 'reviewedAt'}
ALLOWED = {'quality': {'Grade A', 'Grade B', 'Grade C', 'Reject'},
           'maturity': {'Mature Dragon Fruit', 'Immature Dragon Fruit'}}


class Images(Dataset):
    def __init__(self, rows):
        self.rows, self.transform = rows, preprocessing()

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        path = (ROOT / row['image']).resolve()
        if not path.is_relative_to(ROOT) or file_hash(path) != row['fileSha256']:
            raise ValueError('Image path or hash mismatch: ' + row['id'])
        with Image.open(path) as image:
            return self.transform(ImageOps.exif_transpose(image).convert('RGB'))


def read_inputs(peer_paths, reviewer):
    base = json.loads((ROOT / 'research/public-review-manifest.json').read_text())
    lookup = {r['id']: r for r in base}
    assignments = {a['reviewerId']: set(a['recordIds']) for a in json.loads(
        (ROOT / 'research/review-assignments-3.json').read_text())['assignments']}
    peers, provenance, seen = [], [], set()
    for path in peer_paths:
        raw = path.read_bytes()
        rows = json.loads(raw.decode('utf-8-sig'))
        owners = {r.get('reviewer') for r in rows}
        if len(owners) != 1 or reviewer in owners:
            raise ValueError('Require other members completed exports')
        owner = next(iter(owners))
        ids = [r['id'] for r in rows]
        if owner in seen or len(ids) != len(set(ids)) or set(ids) != assignments.get(owner):
            raise ValueError('Peer export does not exactly match its assignment')
        seen.add(owner)
        for row in rows:
            original = lookup[row['id']]
            if any(row.get(k) != v for k, v in original.items() if k not in REVIEW_FIELDS):
                raise ValueError('Peer changed source record: ' + row['id'])
            if row.get('reviewedLabel') not in ALLOWED[row['task']] or not all(row.get(k) for k in REVIEW_FIELDS):
                raise ValueError('Incomplete peer review: ' + row['id'])
        peers.extend(rows)
        provenance.append({'filename': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                           'reviewer': owner, 'count': len(rows)})
    target = [r for r in base if r['id'] in assignments[reviewer]]
    if any(any(row.get(k) for k in REVIEW_FIELDS) for row in target):
        raise ValueError('Refusing to replace existing target reviews')
    return peers, target, provenance


def classifier():
    return make_pipeline(StandardScaler(), LogisticRegression(C=.1, class_weight='balanced', max_iter=2000, random_state=42))


def generate(peer_paths, reviewer, output):
    peers, target, provenance = read_inputs(peer_paths, reviewer)
    output.mkdir(parents=True, exist_ok=False)
    rows = peers + target
    torch.manual_seed(42)
    torch.set_num_threads(4)
    torch.hub.set_dir(ROOT / 'dataset/mendeley-disease/pretrained-cache')
    encoder = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT).eval()
    encoder.classifier = nn.Identity()
    values = []
    with torch.inference_mode():
        for i, images in enumerate(DataLoader(Images(rows), batch_size=48, num_workers=0)):
            values.append(encoder(images).numpy())
            if i % 10 == 0:
                print(f'Encoded {min((i+1)*48,len(rows))}/{len(rows)} assignment/reference images', flush=True)
    features = np.concatenate(values)
    np.savez_compressed(output / 'features.npz', ids=[r['id'] for r in rows], features=features)
    proposals, diagnostics = [], {}
    stored = {}
    for task in ('quality', 'maturity'):
        reference_ids = [i for i, r in enumerate(peers) if r['task'] == task]
        target_ids = [len(peers)+i for i, r in enumerate(target) if r['task'] == task]
        labels = np.array([peers[i]['reviewedLabel'] for i in reference_ids])
        x, xt = features[reference_ids], features[target_ids]
        model = classifier().fit(x, labels)
        probabilities = model.predict_proba(xt)
        names = model.classes_.tolist()
        peer_predictions = []
        diagnostics[task] = {}
        for owner in sorted({r['reviewer'] for r in peers}):
            own = np.array([peers[i]['reviewer'] == owner for i in reference_ids])
            peer_model = classifier().fit(x[own], labels[own])
            peer_predictions.append(peer_model.predict(xt))
            diagnostics[task][owner] = {'referenceCount': int(own.sum()),
                'agreementOnOtherMember': float((peer_model.predict(x[~own]) == labels[~own]).mean()),
                'meaning': 'Agreement between peer labeling patterns, not held-out model accuracy or label truth.'}
        xn = x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)
        xtn = xt / np.maximum(np.linalg.norm(xt, axis=1, keepdims=True), 1e-12)
        similarity = xtn @ xn.T
        stored[task] = {'classes': names, 'coefficients': model[-1].coef_.tolist(),
                        'intercept': model[-1].intercept_.tolist(), 'scalerMean': model[0].mean_.tolist(),
                        'scalerScale': model[0].scale_.tolist()}
        for position, row_index in enumerate(target_ids):
            row = rows[row_index]
            order = np.argsort(probabilities[position])[::-1]
            label, confidence = names[order[0]], float(probabilities[position, order[0]])
            nearest = np.argsort(similarity[position])[-3:][::-1]
            references = [{'id': peers[reference_ids[j]]['id'],
                           'label': peers[reference_ids[j]]['reviewedLabel'],
                           'reviewer': peers[reference_ids[j]]['reviewer'],
                           'image': peers[reference_ids[j]]['image'],
                           'cosineSimilarity': float(similarity[position,j])} for j in nearest]
            reasons = []
            if confidence < .7:
                reasons.append('model score below 0.70; uncalibrated')
            if len({pred[position] for pred in peer_predictions}) != 1:
                reasons.append('models fitted to the two members disagree')
            if sum(r['label'] == label for r in references) < 2:
                reasons.append('nearest visual references do not support a clear majority')
            proposals.append({**row, 'assignedReviewer': reviewer, 'proposedLabel': label,
                              'confidence': confidence, 'reviewPriority': float(1-confidence),
                              'status': 'unverified-model-proposal', 'humanReviewRequired': True,
                              'needsAttention': bool(reasons), 'attentionReasons': reasons,
                              'scores': {names[j]: float(probabilities[position,j]) for j in order},
                              'peerModelLabels': [str(p[position]) for p in peer_predictions],
                              'references': references})
    raw_model = json.dumps(stored, sort_keys=True).encode()
    model_hash = hashlib.sha256(raw_model).hexdigest()
    (output / 'assistance-model.json').write_bytes(raw_model)
    for row in proposals:
        row['modelSha256'] = model_hash
    proposals.sort(key=lambda r: (not r['needsAttention'], r['confidence'], r['id']))
    result = {'schemaVersion': 1, 'purpose': 'AI-assisted review draft only; not human-reviewed ground truth',
              'reviewerId': reviewer, 'createdAt': datetime.now(timezone.utc).isoformat(),
              'referenceFiles': provenance, 'diagnostics': diagnostics,
              'method': 'Frozen ImageNet MobileNetV3-small features and peer-label logistic regression; no grade rules or physical measurements inferred.',
              'limitations': ['All suggestions require confirmation, including high-score suggestions.',
                             'Peer examples span original candidate splits; this helper and its agreement scores are not production evaluation.',
                             'No final source-fruit identities, human reviewer identity, review timestamps or adviser approval are invented.'],
              'counts': dict(Counter(r['task'] for r in proposals)),
              'attentionCounts': dict(Counter(r['task'] for r in proposals if r['needsAttention'])),
              'proposals': proposals}
    (output / 'reviewer-01-ai-assistance.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    (output / 'quality-proposals-for-review-desk.json').write_text(json.dumps(
        {'schemaVersion': 1, 'proposals': [r for r in proposals if r['task']=='quality']}, indent=2)+'\n', encoding='utf-8')
    (output / 'reviewer-01-unreviewed-manifest.json').write_text(json.dumps(target,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['counts','attentionCounts','diagnostics']},indent=2),flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--peers', nargs=2, type=Path, required=True)
    parser.add_argument('--reviewer', default='reviewer-01', choices=['reviewer-01'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    generate(args.peers, args.reviewer, args.output)
